"""Run an offline planning demonstration and export a readable HTML/JSON report."""
import argparse
import html
import json
from pathlib import Path

from tripmate.agents.planning import TravelPlanningAgent
from .application import accept_proposal
from .fixtures import fixture_runtime, FIXTURE_TIME
from .common import money


def render_report(data):
    def esc(value):
        return html.escape(str(value))
    cards = []
    for n, record in enumerate(data["options"], 1):
        v, m = record["version"], record["metrics"]
        rows = "".join(f"<tr><td>{esc(i['productType'])}</td><td>{esc(i['offerId'])}</td><td>{esc(i['startAt'])}<br>{esc(i['endAt'])}</td><td>AUD {esc(i['quotedPrice']['amount'])}</td></tr>" for i in v["items"])
        checks = "".join(f"<li><b>{esc(c['outcome'])}</b> · {esc(c['ruleId'])}: {esc(c['reason'])}</li>" for c in v["validationResults"])
        cards.append(f"<article><div class='tag'>{'推荐方案' if n == 1 else '备选方案 '+str(n)}</div><h2>AUD {esc(v['totalPrice']['amount'])}</h2><p>交通时间 {esc(m['journeyMinutes'])} 分钟 · 模式 {esc(v['rankingMode'])} · 评分 {float(record['ranking']['score']):.3f}</p><p class='muted'>{esc(v['versionId'])}</p><table><thead><tr><th>类型</th><th>资源</th><th>时间</th><th>完整报价</th></tr></thead><tbody>{rows}</tbody></table><details><summary>查看 {len(v['validationResults'])} 项校验和来源</summary><ul>{checks}</ul><pre>{esc(json.dumps(v['sourceReferences'],ensure_ascii=False,indent=2))}</pre></details></article>")
    result = data["result"]
    llm_notice = ('已启用课程模型调用；调用与规划是否成功请查看下方执行记录。'
                  if data.get('modelPlanning') else '未调用真实 LLM。')
    extra = ""
    if "revision" in data:
        extra = "<article><h2>版本修改结果</h2><pre>" + esc(json.dumps(data["revision"], ensure_ascii=False, indent=2)) + "</pre></article>"
    if data.get('modelPlanning'):
        extra += '<article><h2>模型提案与工具校验记录</h2><pre>' + esc(json.dumps(data['modelPlanning'], ensure_ascii=False, indent=2)) + '</pre></article>'
    return """<!doctype html><html lang='zh-CN'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>TripMate · Travel Planning 演示</title><style>
body{margin:0;background:#f2f5f7;color:#172b3a;font:16px/1.6 system-ui,sans-serif}main{max-width:1080px;margin:auto;padding:36px 24px}h1{font-size:36px;margin:10px 0}h2{margin:8px 0}.eyebrow,.tag{color:#087e83;font-weight:700}.notice{padding:16px;background:#fff4d8;border-left:4px solid #d99220;border-radius:6px}article{background:white;padding:24px;border:1px solid #dce4e9;border-radius:12px;margin:22px 0;box-shadow:0 4px 14px #172b3a06}table{width:100%;border-collapse:collapse;font-size:14px}td,th{text-align:left;padding:12px;border-bottom:1px solid #e4e9ed}details{margin-top:20px}summary{cursor:pointer;color:#087e83}.muted{color:#667784;font-size:12px;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}li{margin:6px 0}a{color:#087e83}</style><main><div class='eyebrow'>TRIPMATE AI / MOORE</div><h1>Travel Planning 运行报告</h1>""" + f"<p>Sydney → Melbourne · {esc(data['mode'])} · {esc(result['status'])}</p><div class='notice'><b>FIXTURE 模拟演示</b> · 时钟固定为 {esc(FIXTURE_TIME)}。报价、权限和 Reviewer 均为模拟适配器；{esc(llm_notice)}未预订。本页是运行结果报告，不是团队最终网页。</div>" + "".join(cards) + extra + "<article><h2>排除原因与执行结果</h2><pre>" + esc(json.dumps(result, ensure_ascii=False, indent=2)) + "</pre></article></main></html>"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["BUDGET", "VALUE", "COMFORT"], default="VALUE")
    parser.add_argument("--live-model", action="store_true", help="Course model proposes offer IDs; fixture inventory remains simulated")
    parser.add_argument("--budget", default="900.00")
    parser.add_argument("--revise-budget", help="Simulate a separately confirmed budget change; never auto-adopt")
    parser.add_argument("--accept", action="store_true", help="Explicit simulated acceptance of the recommended initial proposal")
    parser.add_argument("--database", default=":memory:")
    parser.add_argument("--output", type=Path, default=Path("output/planning-demo"))
    args = parser.parse_args()
    case, context, runtime = fixture_runtime(args.mode, args.budget, args.database)
    try:
        if args.live_model:
            from tripmate.adapters.campus import load_local_config, CampusLLMService
            from .campus import ModelPlanningEngine
            load_local_config()
            runtime.planner = ModelPlanningEngine(CampusLLMService(), runtime.clock)
        agent = TravelPlanningAgent(runtime)
        result = agent.handle_case(case)
        options = [runtime.repository.get_version(s["subjectId"]) for s in result["subjects"]]
        data = {"executionMode": "FIXTURE", "mode": args.mode, "result": result, "options": options}
        if args.live_model:
            data['modelPlanning'] = {'model': runtime.planner.client.model,
                'callsAttempted': runtime.planner.client.calls, 'attempts': runtime.planner.attempts,
                'responses': runtime.planner.client.responses,
                'status': result['status'], 'supplierData': 'FIXTURE',
                'rankingScope': 'validated model proposals only; not an exhaustive optimum'}
        if result["status"] == "SUCCESS" and args.accept:
            accepted = accept_proposal(runtime, "demo-traveller", options[0]["version"]["versionId"], None, accepted=True)
            data["acceptedVersionId"] = accepted["version"]["versionId"]
        if result["status"] == "SUCCESS" and args.revise_budget:
            case["caseType"] = "PLAN_REVISION"
            request = context["request"]
            request.update(baselineVersionId=options[0]["version"]["versionId"], requestId="demo-revision", constraintSetVersion=2,
                           budgetCeiling=money(args.revise_budget), confirmedChangedFields=["budgetCeiling"])
            context["spec"]["constraintBindings"]["budget"]["value"] = money(args.revise_budget)
            revised = agent.handle_case(case)
            data["revision"] = {"result": revised, "comparisons": [runtime.repository.get_version(s["subjectId"])["comparison"] for s in revised["subjects"]],
                                "selectedVersionId": runtime.repository.selected(options[0]["version"]["planId"])}
        data["traces"] = runtime.repository.find_by_case(case["caseId"])
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "report.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        (args.output / "report.html").write_text(render_report(data), encoding="utf-8")
        print(result["status"], "-", len(options), "options", "-", (args.output / "report.html").resolve())
        if result["errors"]:
            print(json.dumps(result["errors"], ensure_ascii=False))
        return 0 if result["status"] == "SUCCESS" else 1
    finally:
        runtime.repository.close()


if __name__ == "__main__":
    raise SystemExit(main())

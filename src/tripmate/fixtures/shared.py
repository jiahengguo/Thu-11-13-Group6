"""B03 catalog in private shared storage; never creates or resets Auth accounts."""
from copy import deepcopy
from tripmate.fixtures.b03 import baseline


class SharedFixtureCatalog:
    def __init__(self, repository):
        self.repository = repository

    def reset(self):
        data = baseline()
        with self.repository.transaction() as rows:
            for item in data['entities']:
                rows.put('demo_fixture_entity', item['id'], deepcopy(item))
            rows.put('demo_fixture_catalog', 'B03', {key: deepcopy(value) for key, value in data.items() if key != 'entities'})
            rows.put('demo_fixture_manifest', 'B03', {'entityIds': [item['id'] for item in data['entities']]})
        return self.summary()

    def snapshot(self):
        with self.repository.transaction() as rows:
            catalog = rows.get('demo_fixture_catalog', 'B03')
            manifest = rows.get('demo_fixture_manifest', 'B03')
            if not catalog or not manifest:
                return None
            entities = [rows.get('demo_fixture_entity', key) for key in manifest['entityIds']]
            if any(item is None for item in entities):
                raise ValueError('Fixture manifest references an absent record')
            ids = {item['id'] for item in entities}
            if any(src not in ids or target not in ids for src, _, target in catalog['relations']):
                raise ValueError('Fixture relationship integrity failed')
            if any(not set(item['entityIds']).issubset(ids) for item in catalog['scenarios']):
                raise ValueError('Fixture scenario integrity failed')
            return dict(catalog, entities=entities)

    def summary(self):
        data = self.snapshot()
        if data is None:
            return {'seeded': False, 'simulationOnly': True, 'scenarios': []}
        counts = {}
        for item in data['entities']:
            counts[item['kind']] = counts.get(item['kind'], 0) + 1
        return dict(seeded=True, fixtureVersion=data['fixtureVersion'], fixtureTime=data['fixtureTime'],
                    entityCounts=counts, totalEntities=len(data['entities']), referentialIntegrity='PASS',
                    simulationOnly=True, scenarios=data['scenarios'])

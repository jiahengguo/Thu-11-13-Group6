"""Explicit trusted operator provisioning; requires verified existing Supabase user."""
import argparse
from pathlib import Path
from tripmate.api.settings import Settings
from tripmate.operations.common import OperationsError
from .supabase import Supabase


def main():
    parser=argparse.ArgumentParser(description='Grant Operator access to an explicitly authorised verified account')
    parser.add_argument('--email',required=True)
    parser.add_argument('--env-file',type=Path,default=Path('.env'))
    args=parser.parse_args()
    Settings.load(args.env_file)
    try:
        Supabase.from_env().rpc('tripmate_assign_operator',{'approved_email':args.email.strip()})
    except OperationsError:
        parser.exit(1,'Provisioning did not complete. Confirm the account exists, its email is verified, and migrations are applied.\n')
    print('Operator access assigned and recorded in the private audit log.')


if __name__=='__main__':main()

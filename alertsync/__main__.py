import argparse
import yaml

from .nr_api import (create_or_update_policy,
                     get_policy,
                     conditions_for_policy,
                     update_conditions,
                     find_policy)

from .policy_files import parse, build_document


class VarsAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        result = {}
        for pair in values:
            key, val = pair.split('=')
            result[key] = val
        setattr(namespace, self.dest, result)


def upload(args):
    read_policy, new_conditions = parse(args.yaml_policy.read(),
                                        vars=args.vars)

    policy = create_or_update_policy(read_policy['name'],
                                     read_policy['incident_preference'],
                                     args.policy_id)

    update_conditions(policy['id'], new_conditions)


def download(args):

    if args.policy_name:
        policy = find_policy(args.policy_name)
    else:
        policy = get_policy(args.policy_id)

    conditions = conditions_for_policy(policy['id'])
    document = build_document(policy, conditions)
    yaml_str = yaml.safe_dump(document)
    args.output.write(yaml_str)


def main():
    parser = argparse.ArgumentParser(description='manage new relic alerts')
    subparsers = parser.add_subparsers()

    download_parser = subparsers.add_parser('download')
    policy_query_args = download_parser.add_mutually_exclusive_group(
        required=True)
    policy_query_args.add_argument('--policy-name')
    policy_query_args.add_argument('--policy-id', type=int)
    download_parser.add_argument('--output',
                                 type=argparse.FileType('w'),
                                 default='-')

    download_parser.set_defaults(func=download)

    upload_parser = subparsers.add_parser('upload')
    upload_parser.add_argument('yaml_policy', type=argparse.FileType('r'))
    upload_parser.add_argument('--policy-id', type=int)
    upload_parser.add_argument('--vars', nargs='*', action=VarsAction)

    upload_parser.set_defaults(func=upload)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

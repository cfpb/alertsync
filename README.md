Current status: we are not currently using or maintaining this code



# Alertsync

**Description**:  manage your New Relic alerts, as code

```bash
$ alertsync download --policy-name "API Health" --output api_health.yaml

$ cat api_health.yaml 
incident_preference: PER_CONDITION
name: EXT API Health
nrql_conditions:
- enabled: true
  id: 1283812
  name: No reported health checks
  nrql: {query: SELECT count(*) from APIHealthCheck where environment='ext', since_value: '3'}
  terms:
  - {duration: '10', operator: below, priority: critical, threshold: '1', time_function: any}
  value_function: sum
- enabled: true
  id: 1283797
  name: Any API tests failing
  nrql: {query: SELECT count(*) from APIHealthCheck where success = 0 and environment
      ='ext', since_value: '3'}
  runbook_url: https://insights.newrelic.com/accounts/XXXXXX/dashboards/554146
  terms:
  - {duration: '10', operator: above, priority: critical, threshold: '2', time_function: any}
  value_function: sum

# make some changes, and then...

$ alertsync upload api_health.yaml
```

## Data format

The data format corresponds pretty strictly to the API's (aside from being YAML instead of JSON). A [policy](https://docs.newrelic.com/docs/alerts/rest-api-alerts/new-relic-alerts-rest-api/rest-api-calls-new-relic-alerts#policies) really only has a name, and an "incident preference". The remainder of the file are the conditions grouped by type.

The plain "conditions" refers to [APM, browser, and mobile conditions](https://docs.newrelic.com/docs/alerts/rest-api-alerts/new-relic-alerts-rest-api/rest-api-calls-new-relic-alerts#conditions)

The others are:

- [nrql_conditions](https://docs.newrelic.com/docs/alerts/rest-api-alerts/new-relic-alerts-rest-api/rest-api-calls-new-relic-alerts#conditions-nrql)
- [external_service_conditions](https://docs.newrelic.com/docs/alerts/rest-api-alerts/new-relic-alerts-rest-api/rest-api-calls-new-relic-alerts#ext-services-conditions)
- [synthetics_conditions](https://docs.newrelic.com/docs/alerts/rest-api-alerts/new-relic-alerts-rest-api/rest-api-calls-new-relic-alerts#synthetics-conditions)
- [plugins_conditions](https://docs.newrelic.com/docs/alerts/rest-api-alerts/new-relic-alerts-rest-api/rest-api-calls-new-relic-alerts#plugins-conditions)
- [infrastructure_conditions](https://docs.newrelic.com/docs/infrastructure/new-relic-infrastructure/infrastructure-alert-conditions/rest-api-calls-new-relic-infrastructure-alerts#condition-types)

You should note that [there are condition types not supported by the API](https://docs.newrelic.com/docs/alerts/rest-api-alerts/new-relic-alerts-rest-api/rest-api-calls-new-relic-alerts#excluded).

## Policy Templates

If you include a `--vars` argument with one or more key=value pairs in your `upload` command, then the policy will be interpreted as a Jinja2 template and rendered with those values. For a trivial example, consider a policy snippet that looks like this:

```yaml
name: {{environment.upper()}} Health
incident_preference: PER_CONDITION
nrql_conditions:
- enabled: true
  id: 2810686
  name: No reported health checks
  nrql: {query: SELECT count(*) from HealthCheck where environment='{{environment}}', since_value: '3'}
  terms:
  - {duration: '10', operator: below, priority: critical, threshold: '1', time_function: any}
  value_function: sum
- enabled: true
  id: 2810687
  name: Any tests failing
  nrql: {query: SELECT count(*) from HealthCheck where success = 0 and environment
      ='{{environment}}', since_value: '3'}
  runbook_url: https://insights.newrelic.com/accounts/XXXXXX/dashboards/554146
  terms:
  - {duration: '10', operator: above, priority: critical, threshold: '2', time_function: any}
  value_function: sum
```

The command:

`alertsync upload foo.yaml --vars environment=prod`

Will create an alert policy called 'PRODUCTION HEALTH', with all of the nrql queries limited to results where 'environment' equals 'production'.


## Dependencies

This requires python 3, and the libraries listed in requirements.txt. You can install them with

`pip install -r requirements.txt`

## Installation

In a checkout of this repository, either of these should work:

`python setup.py install`

`pip install .`


## Configuration

The software expects the environment variable 'NR_API_KEY' to exist, and contain a valid New Relic API key

## Usage

There are currently two subcommands, `upload` and `download`

### upload

```bash
$ alertsync upload --help
usage: alertsync upload [-h] [--policy-id POLICY_ID] yaml_policy

positional arguments:
  yaml_policy

optional arguments:
  -h, --help            show this help message and exit
  --policy-id POLICY_ID
```

### download

```bash
$ alertsync download  --help
usage: alertsync download [-h]
                          (--policy-name POLICY_NAME | --policy-id POLICY_ID)
                          [--output OUTPUT]

optional arguments:
  -h, --help            show this help message and exit
  --policy-name POLICY_NAME
  --policy-id POLICY_ID
  --output OUTPUT
```

## Known issues

- We currently aren't managing notification channels at all, those must be configured using newrelic.com.

## Getting help


If you have questions, concerns, bug reports, etc, please file an issue in this repository's Issue Tracker.

## Getting involved


See [CONTRIBUTING](CONTRIBUTING.md).


----

## Open source licensing info
1. [TERMS](TERMS.md)
2. [LICENSE](LICENSE)
3. [CFPB Source Code Policy](https://github.com/cfpb/source-code-policy/)


----

## Credits and references

1. Projects that inspired you
2. Related projects
3. Books, papers, talks, or other sources that have meaningful impact or influence on this project

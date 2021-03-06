import logging

from tdm_ingestion.consumers.tdmq_consumer import TDMQConsumer
from tdm_ingestion.http_client.requests import Requests
from tdm_ingestion.storage.ckan import CkanStorage, RemoteCkan
from tdm_ingestion.tdmq.models import EntityType
from tdm_ingestion.tdmq.remote import Client
from tdm_ingestion.utils import TimeDelta


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-d', help='debug', dest='debug', action='store_true',
                        default=False)

    parser.add_argument('--tdmq_url', dest='tdmq_url', required=True)
    parser.add_argument('--bucket', dest='bucket', required=True, type=float)
    parser.add_argument('--op', dest='operation', required=True)

    time_delta_mapping = {
        'today': TimeDelta.today,
        '1h': TimeDelta.one_hour,
        '1d': TimeDelta.one_day,
        '1w': TimeDelta.one_week,
        '1m': TimeDelta.one_month
    }
    parser.add_argument('--time_delta_before', dest='time_delta_before',
                        choices=time_delta_mapping.keys())

    parser.add_argument('--before', dest='before')
    parser.add_argument('--after', dest='after')
    parser.add_argument('--entity_type', dest='entity_type', required=True,
                        choices=['PointWeatherObserver', 'WeatherObserver',
                                 'EnergyConsumptionMonitor',
                                 'DeviceStatusMonitor'])

    parser.add_argument('--ckan_url', dest='ckan_url', required=True)
    parser.add_argument('--ckan_api_key', dest='ckan_api_key', required=True)
    parser.add_argument('--ckan_dataset', dest='ckan_dataset', required=True)
    parser.add_argument('--ckan_resource', dest='ckan_resource', required=True)
    parser.add_argument(
        '--ckan_description', dest='ckan_description',
        help=('description text; %%{after} and %%{before} are populated by '
              'first and last day (1w and 1m time deltas only)'),
        required=False, default="")
    parser.add_argument('--upsert', dest='upsert', default=False,
                        action='store_true')
    parser.add_argument('--prune', dest='prune', default=False,
                        help='when create a resource with time deltas of 1w or'
                        '1m deletes the related daily reports.',
                        action='store_true')

    args = parser.parse_args()
    logging_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=logging_level)

    logging.info('running with args %s', args.__dict__)

    if args.time_delta_before:
        time_delta = time_delta_mapping[args.time_delta_before]
        before, after = time_delta.get_before_after()
        resource_name = after.strftime(args.ckan_resource)
    else:
        before, after = args.before, args.after
        resource_name = args.ckan_resource

    description_text = args.ckan_description or ''
    if args.ckan_description and args.time_delta_before:

        if "%{after}" in description_text:
            description_text = description_text.replace(
                "%{after}", after.strftime("%Y-%m-%d"))

        if "%{before}" in description_text:
            description_text = description_text.replace(
                "%{before}", before.strftime("%Y-%m-%d"))

    consumer = TDMQConsumer(Client(args.tdmq_url))

    storage = CkanStorage(
        RemoteCkan(args.ckan_url, Requests(), args.ckan_api_key))

    storage.write(
        consumer.poll(
            EntityType(args.entity_type),
            args.bucket, args.operation,
            before, after
        ),
        args.ckan_dataset,
        resource_name,
        description_text,
        args.upsert)

    if args.prune:
        if args.time_delta_before == '1w':
            storage.prune_resources(args.ckan_dataset, resource_name,
                                    after, before, prune_weekly=False)
        elif args.time_delta_before == '1m':
            storage.prune_resources(args.ckan_dataset, resource_name,
                                    after, before, prune_weekly=True)


if __name__ == '__main__':
    main()

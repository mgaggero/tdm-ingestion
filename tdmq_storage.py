import os
from typing import List

import requests
from ingestion import Storage, TimeSeries


class TDMQStorage(Storage):
    def __init__(self, tdmq_url: str):
        self.tdmq_url = tdmq_url

    def write(self, timeseries: List[TimeSeries]):
        requests.post(os.path.join(self.tdmq_url, '/measures'),
                      json=[ts.to_dict() for ts in timeseries]).raise_for_status()
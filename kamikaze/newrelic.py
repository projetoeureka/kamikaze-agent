from __future__ import absolute_import

import datetime
import json
import multiprocessing
import newrelic.agent
import os
import requests
import traceback
import time
import timeit


@newrelic.agent.data_source_factory(name='Kamikaze CPU Usage')
class KamikazeDataSource(object):

    def __init__(self, settings, environ):
        self._timer = None
        self._times = None
        self._frames = []
        self._kamikaze_host = os.environ.get(
            "KAMIKAZE_DATA_COLLECTOR_HOST",
            "http://datacollector.kamikaze.prod.gkn.io",
        )
        self._app_id = os.environ.get("KAMIKAZE_APP_ID")

    def start(self):
        if not self._app_id:
            return

        print "[kamikaze] data source started"
        self._timer = start_timer()
        try:
            self._times = os.times()
        except Exception:
            self._times = None

    def stop(self):
        if not self._app_id:
            return

        print "[kamikaze] data source called"
        self._timer = None
        self._times = None

    def __call__(self):
        if self._times is None or self._app_id is None:
            return ()

        new_times = os.times()
        user_time = new_times[0] - self._times[0]

        elapsed_time = self._timer.restart_timer()

        utilization = user_time / elapsed_time
        print "[kamikaze] times = {}; elapsed_time = {}; utilization = {}".format(
            new_times, elapsed_time, utilization
        )

        while len(self._frames) > 30:
            self._frames.pop(0)

        self._frames.append({
            "instance_id": os.environ["DYNO"],
            "process_id": os.getpid(),
            "type": "web",
            "start_time": (
                datetime.datetime.utcnow() - datetime.timedelta(seconds=elapsed_time)
            ).isoformat(),
            "end_time": datetime.datetime.utcnow().isoformat(),
            "usage": 100 * utilization,
        })

        self._times = new_times
        self._process_uploads()
        return ()

    def _process_uploads(self):
        try:
            print "[kamikaze] uploading {} frames".format(len(self._frames))
            requests.post(
                "{}/apps/{}/cpu-usage".format(
                    self._kamikaze_host.rstrip("/"),
                    self._app_id,
                ),
                data=json.dumps(self._frames),
                headers={"Content-Type": "application/json"},
                timeout=5.0,
            ).raise_for_status()
            self._frames = []
        except:
            print "[kamikaze] unable to upload frame"
            traceback.print_exc()


class _Timer(object):

    def __init__(self):
        self._time_started = time.time()
        self._started = timeit.default_timer()
        self._stopped = None

    def time_started(self):
        return self._time_started

    def stop_timer(self):
        if self._stopped is None:
            self._stopped = timeit.default_timer()
        return self._stopped - self._started

    def restart_timer(self):
        elapsed_time = self.stop_timer()
        self._time_started = time.time()
        self._started = timeit.default_timer()
        self._stopped = None
        return elapsed_time

    def elapsed_time(self):
        if self._stopped is not None:
            return self._stopped - self._started
        return timeit.default_timer() - self._started


def start_timer():
    return _Timer()


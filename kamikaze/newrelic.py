import datetime
import json
import logging
import newrelic.agent
import os
import requests
import timeit

logger = logging.getLogger(__name__)


@newrelic.agent.data_source_factory(name="Kamikaze CPU Usage")
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

        logger.info("data source started")
        self._timer = _Timer()
        self._times = os.times()

    def stop(self):
        if not self._app_id:
            return

        logger.info("data source stopped")
        self._timer = None
        self._times = None

    def __call__(self):
        if self._times is None or self._app_id is None:
            return ()

        new_times = os.times()
        user_time = new_times[0] - self._times[0]

        elapsed_time = self._timer.restart()

        utilization = user_time / elapsed_time
        logger.info(
            "times = %s; elapsed_time = %s; utilization = %s",
            new_times,
            elapsed_time,
            utilization,
        )

        while len(self._frames) > 30:
            self._frames.pop(0)

        self._frames.append(
            {
                "instance_id": os.environ["DYNO"],
                "process_id": os.getpid(),
                "type": "web",
                "start_time": (
                    datetime.datetime.utcnow()
                    - datetime.timedelta(seconds=elapsed_time)
                ).isoformat(),
                "end_time": datetime.datetime.utcnow().isoformat(),
                "usage": 100 * utilization,
            }
        )

        self._times = new_times
        self._process_uploads()
        return ()

    def _process_uploads(self):
        try:
            logger.info("uploading %s frames", len(self._frames))
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
        except Exception:
            logger.error("unable to upload frames", exc_info=True)


class _Timer(object):
    def __init__(self):
        self._time = timeit.default_timer()

    def restart(self):
        _prev_time, self._time = self._time, timeit.default_timer()
        return self._time - _prev_time

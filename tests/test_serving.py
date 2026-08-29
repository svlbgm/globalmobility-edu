import unittest
from unittest.mock import patch

import backend
import serve_backend


class ServingContractTests(unittest.TestCase):
    def tearDown(self):
        backend.pipeline = None

    @patch("serve_backend.serve")
    @patch("serve_backend.RAGPipeline")
    def test_waitress_server_starts_and_stops_pipeline(
        self,
        pipeline_type,
        serve,
    ):
        pipeline = pipeline_type.return_value

        serve_backend.main()

        pipeline.start.assert_called_once_with()
        serve.assert_called_once_with(
            backend.app,
            host="127.0.0.1",
            port=8000,
            threads=2,
        )
        pipeline.stop.assert_called_once_with()
        self.assertIsNone(backend.pipeline)


if __name__ == "__main__":
    unittest.main()

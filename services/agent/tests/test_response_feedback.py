import sqlite3
import unittest
from unittest.mock import patch

from agent.memory import _init_response_feedback_table, save_response_feedback


class ResponseFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        _init_response_feedback_table(self.connection)
        self.connection_patch = patch("agent.memory._get_conn", return_value=self.connection)
        self.connection_patch.start()

    def tearDown(self):
        self.connection_patch.stop()
        self.connection.close()

    def save(self, rating, user_id="user-1", workspace_id="workspace-1"):
        return save_response_feedback(
            request_id="request-1",
            session_id="session-1",
            rating=rating,
            user_id=user_id,
            workspace_id=workspace_id,
            trace_id="trace-1",
            agent_id="agent-1",
        )

    def test_saves_and_revises_a_rating(self):
        first = self.save(1)
        revised = self.save(-1)

        self.assertEqual(first["rating"], 1)
        self.assertEqual(revised["rating"], -1)
        self.assertEqual(first["created_at"], revised["created_at"])
        self.assertEqual(
            self.connection.execute("SELECT COUNT(*) FROM response_feedback").fetchone()[0],
            1,
        )

    def test_feedback_is_scoped_by_user_and_workspace(self):
        self.save(1)
        self.save(-1, user_id="user-2")
        self.save(-1, workspace_id="workspace-2")

        rows = self.connection.execute(
            "SELECT user_id, workspace_id, rating FROM response_feedback ORDER BY user_id, workspace_id"
        ).fetchall()
        self.assertEqual(len(rows), 3)

    def test_rejects_ratings_outside_the_two_vote_options(self):
        with self.assertRaises(ValueError):
            self.save(0)


if __name__ == "__main__":
    unittest.main()
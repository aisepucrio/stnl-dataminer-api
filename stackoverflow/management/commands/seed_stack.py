import os
import json
import requests
from pathlib import Path
from datetime import datetime
from django.core.management.base import BaseCommand
from stackoverflow.models import (
    StackUser,
    StackQuestion,
    StackAnswer,
    StackComment,
)


STACK_API_URL = (
    "https://api.stackexchange.com/2.3/questions"
    "?order=desc&sort=activity&site=stackoverflow"
    "&filter=!-*jbN-o8P3E5"
    "&pagesize=50"
)


def to_datetime(ts):
    """Convert Unix timestamp → timezone-aware datetime or None."""
    if not ts:
        return None
    return datetime.utcfromtimestamp(ts)


class Command(BaseCommand):
    help = "Populate database with real StackOverflow sample data (minimal version)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dump",
            help="Save fetched API data into a local JSON file.",
            action="store_true",
        )
        parser.add_argument(
            "--load",
            help="Load seed data from a local JSON file.",
            type=str,
        )

    def handle(self, *args, **options):
        if options.get("load"):
            result = self._load_from_snapshot(options["load"])
        else:
            result = self._fetch_and_seed(options.get("dump"))

        # ALWAYS write `.stack_seed_done` ONLY inside correct folder
        self._create_done_flag()

        return result

    # ---------------------------------------------------
    # DONE FLAG WRITER
    # ---------------------------------------------------
    def _create_done_flag(self):
        """Create .stack_seed_done inside stackoverflow/management/commands."""
        base_path = Path(__file__).resolve().parent
        done_path = base_path / ".stack_seed_done"

        try:
            with open(done_path, "w", encoding="utf-8") as f:
                f.write("done")
            self.stdout.write(self.style.SUCCESS(f"Created: {done_path}"))
        except Exception as e:
            self.stderr.write(f"Failed to create .stack_seed_done: {e}")

    # ---------------------------------------------------
    # FETCH + SEED
    # ---------------------------------------------------
    def _fetch_and_seed(self, dump):
        self.stdout.write("Fetching StackOverflow data...")

        api_key = os.environ.get("STACK_API_KEY")
        access_token = os.environ.get("STACK_ACCESS_TOKEN")

        params = {}
        if api_key:
            params["key"] = api_key
        if access_token:
            params["access_token"] = access_token

        try:
            response = requests.get(STACK_API_URL, params=params, timeout=20)
            response.raise_for_status()
        except requests.RequestException as e:
            self.stderr.write(f"Failed to fetch API data: {e}")
            return

        data = response.json()
        items = data.get("items", [])
        self.stdout.write(f"Retrieved {len(items)} questions")

        for item in items:
            owner_data = item.get("owner") or {}

            # USER
            user = None
            if owner_data.get("user_id"):
                user, _ = StackUser.objects.get_or_create(
                    user_id=owner_data["user_id"],
                    defaults={
                        "display_name": owner_data.get("display_name"),
                        "reputation": owner_data.get("reputation", 0),
                        "profile_image": owner_data.get("profile_image"),
                        "user_type": owner_data.get("user_type"),
                        "is_employee": owner_data.get("is_employee", False),
                        "link": owner_data.get("link"),
                        "account_id": owner_data.get("account_id"),
                        "badge_counts": owner_data.get("badge_counts"),
                    },
                )

            # QUESTION
            question, _ = StackQuestion.objects.update_or_create(
                question_id=item["question_id"],
                defaults={
                    "title": item.get("title"),
                    "body": item.get("body"),
                    "body_markdown": item.get("body_markdown"),
                    "score": item.get("score", 0),
                    "view_count": item.get("view_count", 0),
                    "answer_count": item.get("answer_count", 0),
                    "comment_count": item.get("comment_count", 0),
                    "up_vote_count": item.get("up_vote_count", 0),
                    "down_vote_count": item.get("down_vote_count", 0),
                    "is_answered": item.get("is_answered", False),
                    "creation_date": to_datetime(item.get("creation_date")),
                    "last_activity_date": to_datetime(item.get("last_activity_date")),
                    "owner": user,
                    "link": item.get("link"),
                    "share_link": item.get("share_link"),
                    "favorite_count": item.get("favorite_count", 0),
                    "accepted_answer_id": item.get("accepted_answer_id"),
                },
            )

            # ANSWERS
            for ans in item.get("answers", []):
                ans_owner_data = ans.get("owner") or {}
                ans_user = None

                if ans_owner_data.get("user_id"):
                    ans_user, _ = StackUser.objects.get_or_create(
                        user_id=ans_owner_data["user_id"],
                        defaults={
                            "display_name": ans_owner_data.get("display_name"),
                            "reputation": ans_owner_data.get("reputation", 0),
                            "profile_image": ans_owner_data.get("profile_image"),
                            "user_type": ans_owner_data.get("user_type"),
                            "is_employee": ans_owner_data.get("is_employee", False),
                        },
                    )

                StackAnswer.objects.update_or_create(
                    answer_id=ans["answer_id"],
                    defaults={
                        "question": question,
                        "body": ans.get("body") or "(no body)",
                        "body_markdown": ans.get("body_markdown") or "(no body)",
                        "score": ans.get("score", 0),
                        "comment_count": ans.get("comment_count", 0),
                        "up_vote_count": ans.get("up_vote_count", 0),
                        "down_vote_count": ans.get("down_vote_count", 0),
                        "is_accepted": ans.get("is_accepted", False),
                        "owner": ans_user,
                        "creation_date": to_datetime(ans.get("creation_date")),
                        "last_activity_date": to_datetime(ans.get("last_activity_date")),
                        "link": ans.get("link") or "https://stackoverflow.com",
                        "share_link": ans.get("share_link") or "https://stackoverflow.com",
                        "title": item.get("title") or "(no title)",
                    },
                )

            # COMMENTS
            for com in item.get("comments", []):
                com_owner = com.get("owner") or {}
                com_user = None

                if com_owner.get("user_id"):
                    com_user, _ = StackUser.objects.get_or_create(
                        user_id=com_owner["user_id"],
                        defaults={"display_name": com_owner.get("display_name")},
                    )

                StackComment.objects.update_or_create(
                    comment_id=com["comment_id"],
                    defaults={
                        "post_type": "question",
                        "post_id": item["question_id"],
                        "body": com.get("body"),
                        "body_markdown": com.get("body_markdown"),
                        "score": com.get("score", 0),
                        "edited": com.get("edited", False),
                        "content_license": com.get("content_license"),
                        "owner": com_user,
                        "creation_date": to_datetime(com.get("creation_date")),
                        "link": com.get("link"),
                        "question": question,
                        "answer": None,
                    },
                )

        # SNAPSHOT
        if dump:
            base_dir = Path(__file__).resolve().parent
            output_path = base_dir / "stack_seed.json"

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            self.stdout.write(f"Snapshot saved to {output_path}")

        self.stdout.write(self.style.SUCCESS("Stack seed data successfully populated."))
        return "done"

    # ---------------------------------------------------
    # LOAD SNAPSHOT
    # ---------------------------------------------------
    def _load_from_snapshot(self, filename):
        self.stdout.write(f"Loading Stack seed data from {filename}")

        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            self.stderr.write(f"Snapshot not found: {filename}")
            return

        items = data.get("items", [])
        self.stdout.write(f"Loading {len(items)} questions...")

        for item in items:
            owner_data = item.get("owner") or {}

            user = None
            if owner_data.get("user_id"):
                user, _ = StackUser.objects.get_or_create(
                    user_id=owner_data["user_id"],
                    defaults={"display_name": owner_data.get("display_name")},
                )

            StackQuestion.objects.update_or_create(
                question_id=item["question_id"],
                defaults={
                    "title": item.get("title"),
                    "owner": user,
                },
            )

        self.stdout.write(self.style.SUCCESS("Snapshot loaded."))
        return "done"

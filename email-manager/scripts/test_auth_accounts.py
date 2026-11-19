"""Offline tests for separate Gmail account credentials."""

import contextlib
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

import auth
import fetch_emails


class AccountAuthTests(unittest.TestCase):
    def test_account_names_cannot_escape_storage(self):
        for address in ("../other", "a@example.com/../../other", "not-an-email"):
            with self.subTest(address=address), self.assertRaises(auth.CredentialStoreError):
                auth._account_token_file(address)
        self.assertEqual(auth._normalize_account(" Nizar@LonghornIP.com "), "nizar@longhornip.com")

    def test_configured_default_wins_over_ssh_legacy_store(self):
        marker = MagicMock()
        marker.is_file.return_value = True
        with patch.dict(os.environ, {"SSH_CONNECTION": "test"}, clear=True), \
                patch.object(auth, "DEFAULT_ACCOUNT_FILE", marker), \
                patch.object(auth, "_default_account", return_value="first@example.com"):
            self.assertEqual(auth._token_file(), auth._account_token_file("first@example.com"))

    def test_account_environment_selects_named_file(self):
        with patch.dict(os.environ, {auth.ACCOUNT_ENV: "second@example.com"}, clear=True):
            self.assertEqual(auth._token_file(), auth._account_token_file("second@example.com"))

    def test_explicit_token_override_is_preserved(self):
        with patch.dict(os.environ, {
            auth.TOKEN_FILE_ENV: "/test/selected.json",
            auth.ACCOUNT_ENV: "second@example.com",
        }, clear=True):
            self.assertEqual(auth._token_file(), Path("/test/selected.json"))

    def test_missing_named_account_never_falls_back(self):
        token = MagicMock()
        token.is_file.return_value = False
        with patch.object(auth, "_account_token_file", return_value=token), \
                patch.object(auth, "_get_secret") as native:
            with self.assertRaises(auth.CredentialStoreError):
                auth.get_credentials(account="missing@example.com")
            native.assert_not_called()

    def test_named_account_refresh_saves_only_selected_file(self):
        token = MagicMock()
        token.is_file.return_value = True
        token.read_text.return_value = '{"test": true}'
        creds = MagicMock(valid=False, expired=True, refresh_token=True)
        with patch.object(auth, "_account_token_file", return_value=token), \
                patch.object(auth.Credentials, "from_authorized_user_info", return_value=creds), \
                patch.object(auth, "Request"), \
                patch.object(auth, "_store_credentials") as store, \
                patch.object(auth, "_get_secret") as native:
            self.assertIs(auth.get_credentials(account="second@example.com"), creds)
            creds.refresh.assert_called_once()
            store.assert_called_once_with(creds, token_file=token)
            native.assert_not_called()

    def test_managed_client_config_does_not_access_native_store(self):
        marker = MagicMock()
        marker.is_file.return_value = True
        client = MagicMock()
        client.is_file.return_value = True
        client.read_text.return_value = "{}"
        with patch.object(auth, "DEFAULT_ACCOUNT_FILE", marker), \
                patch.object(auth, "MANAGED_CLIENT_FILE", client), \
                patch.object(auth, "_systemd_credential_path") as native:
            self.assertEqual(auth._get_secret(auth.CLIENT_ACCOUNT), "{}")
            native.assert_not_called()

    def test_service_rejects_wrong_primary_mailbox(self):
        with patch.object(auth, "get_credentials"), patch.object(auth, "build"), \
                patch.object(auth, "get_account_email", return_value="wrong@example.com"):
            with self.assertRaises(auth.CredentialStoreError):
                auth.get_service(account="second@example.com")

    def test_fetch_all_resolves_each_account_separately(self):
        addresses = ["first@example.com", "second@example.com"]
        output = io.StringIO()
        with patch.object(fetch_emails, "CONFIG_PATH", "unused"), \
                patch.object(fetch_emails, "load_config", return_value={}), \
                patch.object(fetch_emails, "parse_args", return_value={"_account": "all"}), \
                patch.object(fetch_emails, "list_accounts", return_value=addresses), \
                patch.object(fetch_emails, "get_service", side_effect=lambda account: account) as service, \
                patch.object(fetch_emails, "get_account_email", side_effect=lambda item: item), \
                patch.object(fetch_emails, "fetch_account_emails", side_effect=lambda item, address, *args: {"account": address}), \
                contextlib.redirect_stdout(output):
            fetch_emails.main()
        self.assertEqual([entry["account"] for entry in json.loads(output.getvalue())["accounts"]], addresses)
        self.assertEqual([call.kwargs["account"] for call in service.call_args_list], addresses)


if __name__ == "__main__":
    unittest.main()

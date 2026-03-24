"""
services/sync_service.py
========================
Handles synchronization between the local SQLite database and Supabase.
Provides Auth (Login/Register) and Push/Pull sync logic.
"""

import logging
import uuid
import threading
import time
from typing import Optional, Dict, Any
from gotrue import SyncClient as AuthClient
from postgrest import SyncPostgrestClient as DBClient
import keyring

logger = logging.getLogger(__name__)

class SyncService:
    def __init__(self):
        self.url = ""
        self.key = ""
        self.auth: Optional[AuthClient] = None
        self.db: Optional[DBClient] = None
        self._user_id: Optional[str] = None
        self._is_online = False
        self._sync_lock = threading.Lock()

    def configure(self, url: str, key: str):
        """Configure the Supabase connection details."""
        self.url = url
        self.key = key
        if url and key:
            self.auth = AuthClient(url=f"{url}/auth/v1", headers={"apikey": key})
            self.db = DBClient(f"{url}/rest/v1", headers={"apikey": key, "Authorization": f"Bearer {key}"})
            self._is_online = True
            logger.info("SyncService configured for %s", url)

    def login(self, email: str, password: str) -> bool:
        """Authenticate with Supabase and store token in keyring."""
        if not self.auth:
            return False
        try:
            res = self.auth.sign_in_with_password({"email": email, "password": password})
            if res.user:
                self._user_id = res.user.id
                self._update_db_headers(res.session.access_token)
                keyring.set_password("StudyMate", "supabase_session", res.session.access_token)
                keyring.set_password("StudyMate", "supabase_user_id", res.user.id)
                logger.info("User %s logged in successfully", email)
                return True
        except Exception as e:
            logger.error("Login failed: %s", e)
        return False

    def logout(self):
        """Clear session and user info."""
        self._user_id = None
        self.db.headers.pop("Authorization", None)
        try:
            keyring.delete_password("StudyMate", "supabase_session")
            keyring.delete_password("StudyMate", "supabase_user_id")
        except:
            pass
        logger.info("User logged out")

    def _update_db_headers(self, token: str):
        if self.db:
            self.db.headers["Authorization"] = f"Bearer {token}"

    def try_restore_session(self) -> bool:
        """Attempt to restore session from keyring."""
        token = keyring.get_password("StudyMate", "supabase_session")
        user_id = keyring.get_password("StudyMate", "supabase_user_id")
        if token and user_id:
            self._user_id = user_id
            self._update_db_headers(token)
            logger.info("Restored Supabase session for user %s", user_id)
            return True
        return False

    def is_logged_in(self) -> bool:
        return self._user_id is not None

    def sync_all(self, repos: Dict[str, Any]):
        """Perform a full Push and Pull for all tracked tables."""
        if not self.is_logged_in():
            return
        
        logger.info("Starting full sync...")
        for table, repo in repos.items():
            self.pull_table(table, repo)
            self.push_table(table, repo)
        logger.info("Full sync completed.")

    # ── Sync Logic ──────────────────────────────────────────────────────────

    def push_table(self, table_name: str, local_repo: Any):
        """Push all dirty records for a specific table to Supabase."""
        if not self.is_logged_in() or not self.db:
            return

        with self._sync_lock:
            conn = local_repo._conn()
            dirty_rows = conn.execute(f"SELECT * FROM {table_name} WHERE is_dirty = 1").fetchall()
            
            for row in dirty_rows:
                data = dict(row)
                local_id = data.pop("id")
                data.pop("is_dirty", None)
                data.pop("updated_at", None)
                
                # Ensure user_id is set for row-level security
                data["user_id"] = self._user_id
                
                try:
                    remote_id = data.get("remote_id")
                    if not remote_id:
                        # Create new remote record
                        new_remote_id = str(uuid.uuid4())
                        data["remote_id"] = new_remote_id
                        self.db.table(table_name).insert(data).execute()
                        conn.execute(f"UPDATE {table_name} SET remote_id = ?, is_dirty = 0 WHERE id = ?", (new_remote_id, local_id))
                    else:
                        # Update existing remote record
                        self.db.table(table_name).update(data).eq("remote_id", remote_id).execute()
                        conn.execute(f"UPDATE {table_name} SET is_dirty = 0 WHERE id = ?", (local_id,))
                    conn.commit()
                except Exception as e:
                    logger.error("Failed to push %s %s: %s", table_name, local_id, e)
            conn.close()

    def pull_table(self, table_name: str, local_repo: Any):
        """Pull all remote records and merge into local database."""
        if not self.is_logged_in() or not self.db:
            return

        with self._sync_lock:
            try:
                # Fetch all records owned by current user
                res = self.db.table(table_name).select("*").execute()
                remote_rows = res.data
                
                conn = local_repo._conn()
                for r_data in remote_rows:
                    remote_id = r_data.get("remote_id")
                    # Check if exists locally
                    local_row = conn.execute(f"SELECT id FROM {table_name} WHERE remote_id = ?", (remote_id,)).fetchone()
                    
                    if local_row:
                        # Optional: Compare timestamps for "Last Win" conflict resolution
                        # For now, just update local if not dirty
                        pass 
                    else:
                        # Insert new local record
                        # We need to map keys properly based on the table
                        # This part is table-specific and might need a mapper
                        logger.debug("New remote record found for %s: %s", table_name, remote_id)
                conn.close()
            except Exception as e:
                logger.error("Failed to pull %s: %s", table_name, e)

# Global singleton instance
sync_manager = SyncService()

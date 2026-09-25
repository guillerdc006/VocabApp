import pytest

from app.extensions import PROJECT_ROOT, REAL_DB_PATH, _is_real_db, db


class TestGuard:
    def test_reconoce_la_base_real(self):
        assert _is_real_db(str(REAL_DB_PATH))
        assert _is_real_db(REAL_DB_PATH)
        assert _is_real_db(
            PROJECT_ROOT / "instance" / ".." / "instance" / REAL_DB_PATH.name
        )

    def test_no_confunde_bd_temporal(self, tmp_path):
        assert not _is_real_db(tmp_path / "test.db")
        assert not _is_real_db(":memory:")
        assert not _is_real_db(None)

    def test_drop_all_bloqueada_si_el_motor_apunta_a_bd_real(self, app, monkeypatch, tmp_path):
        original = REAL_DB_PATH
        monkeypatch.setattr("app.extensions.REAL_DB_PATH", (tmp_path / "test.db").resolve())
        with app.app_context():
            with pytest.raises(RuntimeError, match="GUARD"):
                db.drop_all()
        monkeypatch.setattr("app.extensions.REAL_DB_PATH", original)

    def test_drop_all_permitida_con_flag_explicito(self, app, monkeypatch, tmp_path):
        monkeypatch.setattr("app.extensions.REAL_DB_PATH", (tmp_path / "test.db").resolve())
        monkeypatch.setenv("ALLOW_DESTRUCTIVE_OPERATIONS", "1")
        with app.app_context():
            db.drop_all()
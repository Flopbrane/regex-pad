"""ファイルの管理処理を検証する。"""

from __future__ import annotations

from fileio.file_manager import FileManager


def test_load_text_uses_requested_encoding(tmp_path) -> None:
    """指定された文字コードでファイルを読み込むことを確認する。"""
    load_file_path = tmp_path / "cp932.txt"
    load_file_path.write_text("日本語", encoding="cp932")

    load_data = FileManager().load_text(load_file_path, "cp932")

    assert load_data == "日本語"


def test_save_text_uses_requested_encoding(tmp_path) -> None:
    """保存の文字列が要求された文字コードを使うことを確認する。"""
    save_file_path = tmp_path / "cp932.txt"

    FileManager().save_text(save_file_path, "日本語", "cp932")

    assert save_file_path.read_text(encoding="cp932") == "日本語"


def test_save_text_uses_requested_newline_code(tmp_path) -> None:
    """保存の文字列が要求された改行のコードを使うことを確認する。"""
    save_file_path = tmp_path / "crlf.txt"

    FileManager().save_text(save_file_path, "a\nb\n", "utf-8", "crlf")

    assert save_file_path.read_bytes() == b"a\r\nb\r\n"

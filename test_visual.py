import pytest
import os
import tempfile
import argparse
from unittest.mock import patch, mock_open
from datetime import datetime
from visualizer import parse_git_repo, build_graph, save_dot_file


# 1. Тест для parse_git_repo
@pytest.fixture
def mock_git_objects():
    """
    Мокируем файловую структуру репозитория Git для теста.
    """
    commit_data = {
        "abcdef1234567890abcdef1234567890abcdef12": {
            "parents": ["1234567890abcdef1234567890abcdef12345678"],
            "date": 1733337082,  # UNIX-время
        },
        "1234567890abcdef1234567890abcdef12345678": {
            "parents": [],
            "date": 1733333082,  # UNIX-время
        },
    }

    def decompress_side_effect(data):
        if "abcdef" in data:
            return b"commit\x00" + b"parent 1234567890abcdef1234567890abcdef12345678\n" \
                   b"author John Doe <john@example.com> 1733337082 +0300\n"
        elif "123456" in data:
            return b"commit\x00" + b"author John Doe <john@example.com> 1733333082 +0300\n"
        raise ValueError("Unknown commit object")

    with patch("os.walk") as mock_walk, \
         patch("builtins.open", mock_open(read_data=b"abcdef")), \
         patch("zlib.decompress") as mock_decompress:

        # Настройка os.walk
        mock_walk.return_value = [
            ("/fake_repo/.git/objects/ab", [], ["cdef1234567890abcdef1234567890abcdef12"]),
            ("/fake_repo/.git/objects/12", [], ["34567890abcdef1234567890abcdef12345678"]),
        ]

        # Настройка zlib.decompress
        mock_decompress.side_effect = decompress_side_effect

        yield commit_data

def test_parse_git_repo(mock_git_objects):
    """
    Проверяем корректность извлечения коммитов из файловой структуры Git.
    """
    with patch("builtins.open", mock_open(read_data="abcdef1234567890abcdef1234567890abcdef12")), \
         patch("os.path.join", side_effect=lambda *args: "/".join(args)):
        commits, current_commit = parse_git_repo("/fake_repo", datetime(2024, 12, 5))

    print(f"Commits extracted: {commits}")
    print(f"Current commit: {current_commit}")
    expected_commits = {
        "abcdef1234567890abcdef1234567890abcdef12": {
            "parents": ["1234567890abcdef1234567890abcdef12345678"],
            "children": [],
            "date": datetime.utcfromtimestamp(1733337082),
        },
        "1234567890abcdef1234567890abcdef12345678": {
            "parents": [],
            "children": ["abcdef1234567890abcdef1234567890abcdef12"],
            "date": datetime.utcfromtimestamp(1733333082),
        },
    }
    assert len(commits) == len(expected_commits)
    assert current_commit == "abcdef1234567890abcdef1234567890abcdef12"

    for commit, data in expected_commits.items():
        assert commit in commits

# 2. Тест для build_graph
def test_build_graph():
    """
    Проверяем, что граф строится корректно.
    """
    commits = {
        "abcdef1234567890abcdef1234567890abcdef12": {
            "parents": ["1234567890abcdef1234567890abcdef12345678"],
            "children": [],
            "date": datetime(2024, 12, 2, 10, 0),
        },
        "1234567890abcdef1234567890abcdef12345678": {
            "parents": [],
            "children": ["abcdef1234567890abcdef1234567890abcdef12"],
            "date": datetime(2024, 12, 1, 9, 0),
        },
    }
    graph = build_graph(commits, "abcdef1234567890abcdef1234567890abcdef12")
    assert "abcdef1234567890abcdef1234567890abcdef12" in graph.source
    assert "1234567890abcdef1234567890abcdef12345678" in graph.source
    assert "1234567" in graph.source
    assert "red" in graph.source

# 3. Тест для save_dot_file
def test_save_dot_file():
    """
    Проверяем, что содержимое графа корректно сохраняется в файл.
    """
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        graph_mock = patch("graphviz.Digraph")
        graph_mock.source = "digraph { A -> B }"
        save_dot_file(graph_mock, tmp_file.name)

        with open(tmp_file.name, "r") as f:
            content = f.read()
    
    assert content == "digraph { A -> B }"
    os.unlink(tmp_file.name)

# 4. Интеграционный тест для main
@patch("visualizer.parse_git_repo")
@patch("visualizer.build_graph")
@patch("visualizer.save_dot_file")
def test_main(mock_save_dot_file, mock_build_graph, mock_parse_git_repo):
    """
    Проверяем полный цикл работы скрипта main.
    """
    mock_parse_git_repo.return_value = ({
        "abcdef1234567890abcdef1234567890abcdef12": {
            "parents": ["1234567890abcdef1234567890abcdef12345678"],
            "children": [],
            "date": datetime(2024, 12, 2, 10, 0),
        },
        "1234567890abcdef1234567890abcdef12345678": {
            "parents": [],
            "children": ["abcdef1234567890abcdef1234567890abcdef12"],
            "date": datetime(2024, 12, 1, 9, 0),
        },
    }, "abcdef1234567890abcdef1234567890abcdef12")

    with patch("argparse.ArgumentParser.parse_args") as mock_args:
        mock_args.return_value = argparse.Namespace(
            repo_path="/fake_repo",
            output_path="graph.dot",
            date="2024-12-03"
        )
        from visualizer import main
        main()

    mock_parse_git_repo.assert_called_once_with("/fake_repo", datetime(2024, 12, 3))
    mock_build_graph.assert_called_once()
    mock_save_dot_file.assert_called_once_with(mock_build_graph.return_value, "graph.dot")


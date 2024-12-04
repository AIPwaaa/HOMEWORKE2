import subprocess
import argparse
from graphviz import Digraph

def get_commits(repo_path, date_filter=None):
    # Формируем команду git log
    git_log_cmd = ["git", "-C", repo_path, "log", "--pretty=format:%H|%P|%ai|%s"]
    if date_filter:
        git_log_cmd.append(f"--before={date_filter}")
    
    result = subprocess.run(git_log_cmd, stdout=subprocess.PIPE, text=True)
    lines = result.stdout.strip().split("\n")
    
    commits = []
    for line in lines:
        hash_, parents, date, message = line.split("|", 3)
        commits.append({
            "hash": hash_,
            "parents": parents.split() if parents else [],
            "date": date,
            "message": message
        })
    
    return commits

def build_graph(commits):
    graph = Digraph(format="png")
    commits = sorted(commits, key=lambda c: c["date"])
    
    for commit in commits:
        graph.node(commit["hash"], f'{commit["hash"][:7]}\n{commit["date"]}\n{commit["message"]}')
        for parent in commit["parents"]:
            graph.edge(parent, commit["hash"])
    
    return graph

def main():
    parser = argparse.ArgumentParser(description="Git Dependency Graph Visualizer")
    parser.add_argument("--repo-path", required=True, help="Path to the git repository")
    parser.add_argument("--graphviz-path", required=True, help="Path to the Graphviz dot executable")
    parser.add_argument("--output-path", required=True, help="Path to output DOT file")
    parser.add_argument("--date", required=True, help="Filter commits before this date (YYYY-MM-DD)")

    args = parser.parse_args()

    # Получаем коммиты
    commits = get_commits(args.repo_path, args.date)
    # Создаём граф
    graph = build_graph(commits)
    # Сохраняем результат
    graph.render(args.output_path, cleanup=True)

if __name__ == "__main__":
    main()

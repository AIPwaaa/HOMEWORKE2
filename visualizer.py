import os
import zlib
import argparse
from graphviz import Digraph
from datetime import datetime, timedelta


def parse_git_repo(repo_path, date_filter=None):
    git_path = os.path.join(repo_path, ".git")

    with open(os.path.join(git_path, "HEAD"), "r") as f:
        ref = f.readline().strip().split(" ")[-1]
    with open(os.path.join(git_path, ref), "r") as f:
        current_commit = f.readline().strip()

    print(f"Current commit: {current_commit}")

    commits = {}
    objects_path = os.path.join(git_path, "objects")
    for root, _, files in os.walk(objects_path):
        for file in files:
            obj_path = os.path.join(root, file)
            with open(obj_path, "rb") as f:
                try:
                    data = zlib.decompress(f.read())
                    if data.startswith(b"commit"):
                        _, content = data.split(b"\x00", 1)
                        lines = content.decode().split("\n")
                        parents = [
                            line.split(" ")[1] for line in lines if line.startswith("parent")
                        ]
                        date_line = next(line for line in lines if line.startswith("author"))
                        
                        date_parts = date_line.split(">")[1].strip().split(" ")
                        timestamp = int(date_parts[0])
                        timezone_offset = date_parts[1]
                        commit_date = datetime.utcfromtimestamp(timestamp) + timedelta(
                            hours=int(timezone_offset[:3]), minutes=int(timezone_offset[0] + timezone_offset[3:])
                        )

                        commit_hash = os.path.basename(root) + file
                        
                        if date_filter and commit_date > date_filter:
                            continue

                        commits[commit_hash] = {
                            "parents": parents,
                            "children": [],
                            "date": commit_date,
                        }

                        print(f"Parsed commit: {commit_hash}, Date: {commit_date}")
                except Exception as e:
                    print(f"Error processing {obj_path}: {e}")

    for commit, data in commits.items():
        for parent in data["parents"]:
            if parent in commits:
                commits[parent]["children"].append(commit)

    return commits, current_commit

def build_graph(commits, current_commit):
    graph = Digraph(format="dot")
    graph.attr(rankdir="TB")

    commits = sorted(commits.items(), key=lambda c: c[1]["date"])
    for index, (commit, data) in enumerate(commits, start=1):
        if commit == current_commit:
            color = "red"
        elif data["children"]:
            color = "blue"
        else:
            color = "green"

        label = f'#{index}\n{commit[:7]}\n{data["date"].strftime("%Y-%m-%d %H:%M:%S")}'
        graph.node(commit, label=label, color=color, style="filled")
        for parent in data["parents"]:
            graph.edge(parent, commit)

    return graph

def save_dot_file(graph, output_path):
    with open(output_path, "w") as f:
        f.write(graph.source)


def main():
    parser = argparse.ArgumentParser(description="Git Dependency Graph Visualizer")
    parser.add_argument("--repo-path", required=True, help="Path to the git repository")
    parser.add_argument("--output-path", required=True, help="Path to save the DOT file")
    parser.add_argument("--date", required=True, help="Filter commits before this date (YYYY-MM-DD)")

    args = parser.parse_args()
    date_filter = datetime.strptime(args.date, "%Y-%m-%d")
    commits, current_commit = parse_git_repo(args.repo_path, date_filter)
    graph = build_graph(commits, current_commit)
    save_dot_file(graph, args.output_path)

    print(f"DOT file saved to: {args.output_path}")


if __name__ == "__main__":
    main()

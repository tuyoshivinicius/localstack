from localstack.plugin.repository import inject_to_path

from .localstack import create_with_plugins


def main():
    inject_to_path()
    cli = create_with_plugins()
    cli()


if __name__ == "__main__":
    main()

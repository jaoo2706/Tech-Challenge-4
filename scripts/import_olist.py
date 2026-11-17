"""Importa as duas tabelas usadas no projeto a partir do ZIP da Olist."""
import argparse
import shutil
from pathlib import Path, PurePosixPath
from zipfile import ZipFile


TABLES = ("olist_order_reviews_dataset.csv", "olist_orders_dataset.csv")


def import_archive(archive, destination):
    destination = Path(destination)
    with ZipFile(archive) as bundle:
        members = {}
        for table in TABLES:
            options = [info for info in bundle.infolist()
                       if not info.is_dir() and PurePosixPath(info.filename).name == table]
            if len(options) != 1:
                raise ValueError(f"Esperada uma cópia de {table} no ZIP. Encontradas {len(options)}.")
            members[table] = options[0]
        destination.mkdir(parents=True, exist_ok=True)
        for table, member in members.items():
            temporary = destination / f"{table}.part"
            try:
                with bundle.open(member) as source, temporary.open("wb") as target:
                    shutil.copyfileobj(source, target)
                temporary.replace(destination / table)
            finally:
                temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip", type=Path)
    parser.add_argument("--destination", default="data/raw", type=Path)
    args = parser.parse_args()
    import_archive(args.zip, args.destination)

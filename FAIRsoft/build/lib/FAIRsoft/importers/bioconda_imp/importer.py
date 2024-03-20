from .importer_recipes import process_recipes


def import_data():
    # ------- 1. recipes -----------------------
    # 1.1 Set recipes' path
    process_recipes()

if __name__=='__main__':
    import_data()
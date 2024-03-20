
import bioconductor_imp.importer as bioconductor
import bioconda_imp.importer as bioconda
import bioconda_biotools_galaxy_imp.importer as opeb_tools
import toolshed_imp.importer as toolshed
import repositories_imp.importer as repos
import opeb_metrics_imp.importer  as opeb_metrics
import sourceforge_imp.importer as sf

def execute_importation(label):
    '''
    Decorator to inform when importation stats and finishes
    '''
    def decorator(func):
        def wrapper():
            print(f'{label} importation starting...')
            func()
            print(f"{label} importation done")
        return wrapper
    return decorator

if __name__ == '__main__':
    # Runs all importators one after another

    importers = [
        bioconductor,
        bioconda,
        opeb_tools,
        toolshed,
        repos,
        opeb_metrics,
        sf
        ]
    
    for imp in importers:
        execute_importation(str(imp))(imp.import_data())

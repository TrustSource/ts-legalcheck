import sys

from pathlib import Path

def download_osadl_data():
    from . import download_lang, download_license
    
    output_dir = sys.argv[1]

    download_lang(output_dir)
    download_license(output_dir)


def transform_osadl_data():
    from . import create_defs

    input_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])

    if not input_dir.exists():
        print(f"Input directory {input_dir} does not exist.")
        sys.exit(1)

    if not output_dir.exists():
        print(f"Output directory {output_dir} does not exist. Creating it.")
        output_dir.mkdir(parents=True)
    
    create_defs(input_dir, output_dir)


def create_processed_checklist():
    from . import create_processed_file
    
    input_file = Path(sys.argv[1])        
    output_dir = Path(sys.argv[3])

    if not output_dir.exists():
        print(f"Processed output directory {output_dir} does not exist. Creating it.")
        output_dir.mkdir(parents=True)

    create_processed_file(input_file, output_dir)


transform_osadl_data()

# if len(sys.argv) > 3:
    # create_processed_checklist()
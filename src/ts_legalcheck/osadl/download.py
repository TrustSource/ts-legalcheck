"""
Module for downloading and managing OSADL (Open Source Automation Development Lab) data.
"""

import os
import urllib.parse
import urllib.request

from pathlib import Path
from typing import List, Optional


def download_files_from_url_list(url_list_url: str, output_directory: str) -> List[str]:
    """
    Download a text file containing URLs and then download each listed file.
    
    A subdirectory will be created within the output directory based on the name 
    of the URL list file (without extension). For example, if the URL list file 
    is named "urls.txt", a folder named "urls" will be created inside the output 
    directory, and all downloaded files will be stored there.
    
    Args:
        url_list_url: URL of the text file containing a list of URLs (one per line)
        output_directory: Base directory where a subdirectory will be created for downloads
        
    Returns:
        List of successfully downloaded file paths
        
    Raises:
        urllib.error.URLError: If there's an error downloading files
        OSError: If there's an error creating directories or writing files
    """
    # Extract the filename from the URL list URL and create subdirectory
    parsed_list_url = urllib.parse.urlparse(url_list_url)
    list_filename = os.path.basename(parsed_list_url.path)
    
    # Remove file extension to create folder name
    if list_filename:
        folder_name = os.path.splitext(list_filename)[0]
    else:
        folder_name = "downloads"
    
    # Create output directory structure: output_directory/folder_name/
    output_path = Path(output_directory) / folder_name
    output_path.mkdir(parents=True, exist_ok=True)
    
    downloaded_files = []
    
    try:
        # Download the URL list file
        print(f"Downloading URL list from: {url_list_url}")
        with urllib.request.urlopen(url_list_url) as response:
            url_list_content = response.read().decode('utf-8')
        
        # Parse URLs from the content (one URL per line)
        urls = [url.strip() for url in url_list_content.splitlines() if url.strip()]
        
        print(f"Found {len(urls)} URLs to download")
        
        # Download each file
        for i, url in enumerate(urls, 1):
            try:
                # Extract filename from URL
                parsed_url = urllib.parse.urlparse(url)
                filename = os.path.basename(parsed_url.path)
                
                # If no filename in URL, generate one
                if not filename:
                    filename = f"file_{i}"
                
                # Construct output file path
                output_file_path = output_path / filename
                
                print(f"Downloading [{i}/{len(urls)}]: {url} -> {filename}")
                
                # Download the file
                urllib.request.urlretrieve(url, output_file_path)
                downloaded_files.append(str(output_file_path))
                
            except Exception as e:
                print(f"Error downloading {url}: {e}")
                continue
                
    except Exception as e:
        print(f"Error downloading URL list from {url_list_url}: {e}")
        raise
    
    print(f"Successfully downloaded {len(downloaded_files)} files to {output_path}")
    return downloaded_files


def download_file(url: str, output_path: str, filename: Optional[str] = None) -> str:
    """
    Download a single file from a URL.
    
    Args:
        url: URL of the file to download
        output_path: Directory where the file will be stored
        filename: Optional custom filename. If not provided, extracted from URL
        
    Returns:
        Path to the downloaded file
        
    Raises:
        urllib.error.URLError: If there's an error downloading the file
        OSError: If there's an error creating directories or writing files
    """
    # Create output directory if it doesn't exist
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine filename
    if not filename:
        parsed_url = urllib.parse.urlparse(url)
        filename = os.path.basename(parsed_url.path)
        if not filename:
            filename = "downloaded_file"
    
    # Construct full file path
    file_path = output_dir / filename
    
    # Download the file
    urllib.request.urlretrieve(url, file_path)
    
    return str(file_path)
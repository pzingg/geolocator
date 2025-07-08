from bs4 import BeautifulSoup
import csv
import re
import requests
import sys
from typing import Dict, Optional, List, Tuple
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

def download_and_parse_kml(kml_url: str) -> List[Dict[str, any]]:
    """
    Download a KML file and parse Placemark elements to extract name and href information.
    
    Args:
        kml_url (str): URL of the KML file to download
        
    Returns:
        List of Dicts, where each Dict contains the following keys:
        - name: Text from the Placemark's 'name' sub-element
        - href: 'href' attribute from the Placemark's 'a' sub-element
        - latitude: latitude from the Placemark's 'coordinates' sub-element
        - longitude: longitude from the Placemark's 'coordinates' sub-element
    """
    
    results = []
    
    try:
        # Download the KML file
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(kml_url, headers=headers)
        response.raise_for_status()
        
        # Parse the XML content
        root = ET.fromstring(response.content)
        
        # Define KML namespace (KML files typically use this namespace)
        kml_namespace = {'kml': 'http://www.opengis.net/kml/2.2'}
        
        # Try to find namespace in the root element if not standard
        if root.tag.startswith('{'):
            # Extract namespace from root tag
            namespace_match = re.match(r'\{([^}]+)\}', root.tag)
            if namespace_match:
                namespace_uri = namespace_match.group(1)
                kml_namespace = {'kml': namespace_uri}
        
        # Find all Placemark elements - try with and without namespace
        placemarks = root.findall('.//kml:Placemark', kml_namespace)
        if not placemarks:
            placemarks = root.findall('.//Placemark')
        
        for placemark in placemarks:
            result = {
                'name': None,
                'href': None,
                'latitude': None,
                'longitude': None
            }
            
            # Extract name - try with and without namespace
            name_value = None
            name_element = placemark.find('kml:name', kml_namespace)
            if name_element is None:
                name_element = placemark.find('name')
            if name_element is not None:
                name_value = name_element.text
            if name_value:
                result['name'] = name_value.strip()
            
            # Look for href in description or other elements
            # The href might be in the description as HTML content
            description_element = placemark.find('kml:description', kml_namespace)
            if description_element is None:
                description_element = placemark.find('description')
            
            href_value = None
            if description_element is not None:
                links = description_element.findall('./*/{*}a')
                for link in links:
                    href_value = link.get('href')
                    break

            # Clean up the extracted value
            if href_value:
                href_value = href_value.strip()
                
                # If href is relative, make it absolute
                if href_value.startswith('/') or not href_value.startswith('http'):
                    base_url = f"{urlparse(kml_url).scheme}://{urlparse(kml_url).netloc}"
                    href_value = urljoin(base_url, href_value)
                
                result['href'] = href_value

            # Look for coordinates in the format "lng, lat"
            coords_pattern = r'([-+]?\d+\.?\d*),\s*([-+]?\d+\.?\d*)'
            coordinates = placemark.findall('./{*}Point/{*}coordinates')
            for coords in coordinates:
                coords_match = re.search(coords_pattern, coords.text)        
                if coords_match:
                    result['latitude'] = float(coords_match.group(2).strip())
                    result['longitude'] = float(coords_match.group(1).strip())
                    break

            # Add to results if we have both name and href
            if result['name'] and result['href']:
                results.append(result)
    
    except requests.RequestException as e:
        print(f"Error downloading KML file: {e}")
    except ET.ParseError as e:
        print(f"Error parsing KML XML: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    return results

def get_waterfall_data(aside: ET.Element) -> Dict[str, str]:
    data = {}
    trs = aside.find_all('tr')
    for tr in trs:
        tds = tr.find_all('td')
        if len(tds) == 2:
            key = tds[0].text.strip()
            if key:
                value = tds[1].text.strip()
                data[key] = value
    return data

def scrape_waterfall_info(name: str, url: str, id_prefix: str, data: Dict[str, any]) -> Dict[str, any]:
    """
    Scrape waterfall information from a World Waterfall Database detail page.
    
    Args:
        name (str): The name of the waterfall
        url (str): The URL of the waterfall detail page
        data (Dict): Optional 'latitude', and 'longitude' defaults
        
    Returns:
        Dict containing the following keys:
        - id: Unique ID, like "CA-4940"
        - name: Name of the waterfall
        - wwd_url: URL of the waterfall deatails page
        - county: County where the waterfall is located
        - state: State where the waterfall is located  
        - country: Country where the waterfall is located
        - latitude: Latitude in decimal degrees
        - longitude: Longitude in decimal degrees
        - form: The waterfall's form/type
        - watershed: The watershed the waterfall belongs to
        - stream: The stream the waterfall is on
    """
    
    # Initialize result dictionary
    result = {
        'id': None,
        'name': name,
        'wwd_url': url,
        'county': None,
        'state': None,
        'country': None,
        'latitude': data.get('latitude'),
        'longitude': data.get('longitude'),
        'form': None,
        'watershed': None,
        'stream': None
    }

    wwd_id_match = re.search(r'[/-](\d+)$', url)
    if wwd_id_match:
        wwd_id = wwd_id_match.group(1)
        result['id'] = f"{id_prefix}-{wwd_id}"
    else:
        raise RuntimeError(f"No id number parsed from {url}")

    try:
        # Fetch the webpage
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract location information from the page title/header
        # Look for the location text that appears near the waterfall name
        location_text = None
        
        # Try to find location in the main content area
        main_content = soup.find('div', class_='content') or soup.find('main') or soup.body
        if main_content:
            # Look for text patterns that match "County, State, Country"
            text_content = main_content.get_text()
            
            # Pattern to match location format: "County, State, Country"
            location_pattern = r'([^,\n]+County),\s*([^,\n]+),\s*([^,\n]+)'
            location_match = re.search(location_pattern, text_content)
            
            if location_match:
                result['county'] = location_match.group(1).strip()
                result['state'] = location_match.group(2).strip()
                result['country'] = location_match.group(3).strip()
        
        sidebar = soup.find('aside', class_='waterfall-info-sidebar')
        if sidebar:
            waterfall_data = get_waterfall_data(sidebar)

            # Extract coordinates
            coordinates = waterfall_data.get('Location')
            if coordinates:
                # Look for coordinates in the format "lat, lng"
                coords_pattern = r'([-+]?\d+\.?\d*),\s*([-+]?\d+\.?\d*)'
                coords_match = re.search(coords_pattern, coordinates)
        
                if coords_match:
                    result['latitude'] = float(coords_match.group(1).strip())
                    result['longitude'] = float(coords_match.group(2).strip())
        
            result['form'] = waterfall_data.get('Form')
            result['watershed'] = waterfall_data.get('Watershed')
            result['stream'] = waterfall_data.get('Stream')
        
        return result
        
    except requests.RequestException as e:
        print(f"Error fetching URL: {e}")
        return result
    except Exception as e:
        print(f"Error parsing waterfall data: {e}")
        return result

# Example usage
if __name__ == "__main__":
    urls = [
        ('CA', 'https://www.worldwaterfalldatabase.com/api/United-States/California/getKML'),
        ('OR', 'https://www.worldwaterfalldatabase.com/api/United-States/Oregon/getKML'),
        ('WA', 'https://www.worldwaterfalldatabase.com/api/United-States/Washington/getKML')
    ]

    fields = [
        'id',
        'name',
        'county',
        'state',
        'country',
        'latitude',
        'longitude',
        'watershed',
        'stream',
        'form',
        'wwd_url'
    ]

    with open('waterfalls.csv', 'w', newline='', encoding='utf-8') as f:
        dict_writer = csv.DictWriter(f, fieldnames=fields)
        dict_writer.writeheader()

        for id_prefix, kml_url in urls:
            print(f"Attempting to parse {kml_url}...")
            print("=" * 50)
            
            # Try the main function first
            placemark_data = download_and_parse_kml(kml_url)
            
            if placemark_data:
                print(f"Found {len(placemark_data)} waterfalls:")
                for data in placemark_data:
                    waterfall_data = scrape_waterfall_info(data['name'], data['href'], id_prefix, data)
                    
                    print()
                    print("Waterfall Information:")
                    print("=" * 30)
                    for key, value in waterfall_data.items():
                        print(f"{key}: {value}")

                    dict_writer.writerow(waterfall_data)
            else:
                print(f"{kml_url}: No waterfall data found.")
    


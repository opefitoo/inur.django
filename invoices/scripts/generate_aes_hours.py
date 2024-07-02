import os
import xml.etree.ElementTree as ET
from collections import defaultdict

# Folder containing the XML files
folder_path = '/Users/mehdi/Downloads/compta 2023/retours AD/'

# Mapping table with hours per codeActePaye
hours_mapping = {
    "AEVF00": 0.29762,
    "AEVF01": 0.66667,
    "AEVF02": 1.00000,
    "AEVF03": 1.33333,
    "AEVF04": 1.66667,
    "AEVF05": 2.00000,
    "AEVF06": 2.33333,
    "AEVF07": 2.66667,
    "AEVF08": 3.00000,
    "AEVF09": 3.33333,
    "AEVF10": 3.66667,
    "AEVF11": 4.00000,
    "AEVF12": 4.33333,
    "AEVF13": 4.66667,
    "AEVF14": 5.00000,
    "AEVF15": 5.30952,
    "AEVFSP": 1.85714
}

# Initialize a dictionary to hold the grouped results and totals
grouped_results = defaultdict(list)
totals_by_code = defaultdict(lambda: {'count': 0, 'total_montantBrut': 0, 'total_montantNet': 0, 'total_hours': 0})


# Function to calculate hours for AAII based on 'nombre'
def calculate_hours_for_aaii(nombre):
    return nombre / 2.0


# Iterate over each XML file in the folder
for filename in os.listdir(folder_path):
    if filename.endswith('.xml'):
        file_path = os.path.join(folder_path, filename)

        # Load and parse the XML file
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Iterate over each prestation element in the XML
        for prestation in root.findall('.//prestation'):
            codeActePaye = prestation.find('codeActePaye').text
            paiementPrestation = prestation.find('paiementPrestation')
            montantBrut = float(paiementPrestation.find('montantBrut').text)
            nombre = int(paiementPrestation.find('nombre').text)

            # Check if codeActePaye contains 'AEVF' or 'AAII' and montantBrut is not 0
            if ('AEVF' in codeActePaye or 'AAII' in codeActePaye or 'AMD' in codeActePaye) and montantBrut != 0:
                grouped_results[codeActePaye].append({
                    'reference': prestation.find('referencePrestation').text,
                    'montantBrut': montantBrut,
                    'montantNet': float(paiementPrestation.find('montantNet').text),
                    'nombre': nombre
                })

                # Update totals
                totals_by_code[codeActePaye]['count'] += 1
                totals_by_code[codeActePaye]['total_montantBrut'] += montantBrut
                totals_by_code[codeActePaye]['total_montantNet'] += float(paiementPrestation.find('montantNet').text)

                if 'AEVF' in codeActePaye:
                    totals_by_code[codeActePaye]['total_hours'] += hours_mapping.get(codeActePaye, 0)
                elif 'AAII' in codeActePaye:
                    totals_by_code[codeActePaye]['total_hours'] += calculate_hours_for_aaii(nombre)
                elif 'AMDGG' in codeActePaye:
                    totals_by_code[codeActePaye]['total_hours'] += (nombre / 2.0)

# Print the grouped results and totals
for code, prestations in grouped_results.items():
    print(f"CodeActePaye: {code}")
    for prestation in prestations:
        print(
            f"  Reference: {prestation['reference']}, MontantBrut: {prestation['montantBrut']}, MontantNet: {prestation['montantNet']}, Nombre: {prestation['nombre']}")
    print(f"  Total count: {totals_by_code[code]['count']} for {code}")
    print(f"  Total MontantBrut: {totals_by_code[code]['total_montantBrut']} for {code}")
    print(f"  Total MontantNet: {totals_by_code[code]['total_montantNet']} for {code}")
    print(f"  Total Hours: {totals_by_code[code]['total_hours']} for {code}")

# Return the grouped results and totals as dictionaries
grouped_results_dict = dict(grouped_results)
totals_by_code_dict = dict(totals_by_code)

# calculate the total hours
total_hours = sum([v['total_hours'] for v in totals_by_code.values()])
print(f"Total Hours: {total_hours}")


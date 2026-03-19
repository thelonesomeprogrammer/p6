import csv
import xml.etree.ElementTree as ET

def kxml_to_csv(xml_file_path, output_csv_path):
    # Parse the XML file
    tree = ET.parse(xml_file_path)
    root = tree.getroot()
    
    # 1. Extract X-Axis data (Time)
    x_axis = root.find(".//X_Axis")
    x_name = x_axis.find("Header/Name").text
    x_unit = x_axis.find("Header/Unit").text
    x_values = [v.text for v in x_axis.findall("Values/float")]
    
    # 2. Extract Y-Axes data
    headers = [f"{x_name} ({x_unit})"]
    all_columns = [x_values]
    
    for axis in root.findall(".//Y_AxesList/AxisData"):
        y_name = axis.find("Header/Name").text
        y_unit = axis.find("Header/Unit").text
        headers.append(f"{y_name} ({y_unit})")
        
        y_values = [v.text for v in axis.findall("Values/float")]
        all_columns.append(y_values)

    # 3. Write to CSV
    # zip(*all_columns) transposes the list of columns into rows
    with open(output_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(zip(*all_columns))

    print(f"Successfully converted {xml_file_path} to {output_csv_path}")


if __name__ == "__main__":
    # Example usage
    xml_file = "data/_002.KXML"  # Replace with your KXML file path
    output_csv = "output.csv"  # Desired output CSV file path
    kxml_to_csv(xml_file, output_csv)

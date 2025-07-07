import csv
import re
import os
from datetime import datetime
import fitz  # PyMuPDF

# Define input and output paths (anonymized)
pdf_directory = r'PATH_TO_PDF_FOLDER'
csv_file_path = r'PATH_TO_CSV_SCHEMA_FILE'
output_directory = r'PATH_TO_OUTPUT_FOLDER'

def read_text_from_pdf(pdf_path):
    document = fitz.open(pdf_path)
    text = ""
    for page_num in range(document.page_count):
        page = document.load_page(page_num)
        text += page.get_text("text")
    return text

def read_csv_to_list(file_path):
    data = []
    with open(file_path, 'r', encoding='cp1252') as file:
        reader = csv.reader(file, delimiter='|')
        headers = next(reader)
        for row in reader:
            data.append(row)
    return headers, data

def extract_text_between_ids(text, csv_data, iterations=250):
    results = []
    yes_count = no_count = na_count = not_found_count = multivalue_count = 0
    special_cases = [("DOC-1", "DOC-2"), ("DOC-4", "DOC-5")]

    for i in range(min(iterations, len(csv_data) - 1)):
        id_n = csv_data[i][0]
        id_n1 = csv_data[i + 1][0]
        start_pos = text.find(id_n)
        end_pos = text.find(id_n1, start_pos)

        if start_pos != -1 and end_pos != -1:
            extracted_text = text[start_pos:end_pos]
            if (id_n, id_n1) in special_cases:
                answer = extracted_text.replace(id_n, '').replace(id_n1, '').replace(csv_data[i][1], '').strip()
                multivalue = ""
            else:
                matches = re.findall(r'(Yes|No|See Note|See Notes|N/A)', extracted_text)
                if matches:
                    question_mark_pos = extracted_text.find('?')
                    matches_after_q = [m for m in matches if extracted_text.find(m, question_mark_pos) != -1] if question_mark_pos != -1 else []
                    answer = matches_after_q[1] if id_n in ["CSUP-1", "PLOK-1"] and matches_after_q and matches_after_q[0] == "N/A" else (matches_after_q[0] if matches_after_q else matches[0])
                    multivalue = "Multivalue" if len(matches) > 1 else ""
                    yes_count += (answer == "Yes")
                    no_count += (answer == "No")
                    na_count += (answer == "N/A")
                else:
                    answer, multivalue = "Not found", ""
                    not_found_count += 1
            results.append([id_n, csv_data[i][1], answer, multivalue])
        else:
            results.append([id_n, csv_data[i][1], "Not found", ""])
            not_found_count += 1
    return results

def write_summary_to_csv(all_results, headers, output_file_path):
    headers = ["Filename"] + headers
    with open(output_file_path, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        for result in all_results:
            result = [item.replace(" __", "").replace("\n__", "") for item in result]
            writer.writerow(result)

def main():
    headers, csv_data = read_csv_to_list(csv_file_path)
    all_results = []

    for filename in os.listdir(pdf_directory):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(pdf_directory, filename)
            try:
                text = read_text_from_pdf(pdf_path)
                results = extract_text_between_ids(text, csv_data)
                data = [filename] + [result[2] for result in results]
            except Exception:
                data = [filename] + [""] * (len(csv_data) - 1)
            all_results.append(data)

    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
    output_file = os.path.join(output_directory, f"export_{timestamp}.csv")
    headers = [result[0] for result in results]
    write_summary_to_csv(all_results, headers, output_file)

if __name__ == "__main__":
    main()

from flask import Flask, render_template, request, send_file
import pandas as pd
import os
import json
from datetime import datetime
import io

app = Flask(__name__)

# Global storage for all zones
all_zones = []

# Output folder: Downloads folder
downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")
os.makedirs(downloads_folder, exist_ok=True)

def generate_locations_data():
    """Generate sorted locations data"""
    if not all_zones:
        return None
    
    data = []
    for zone in all_zones:
        zg_rz_val = zone["zg_rz"]
        for ai, ranges in zone["ai_dict"].items():
            for bi in range(ranges["bi"][0], ranges["bi"][1] + 1):
                for ro in range(ranges["ro"][0], ranges["ro"][1] + 1):
                    location = f"{zg_rz_val}{ai:02d}{bi:02d}{ro:02d}"
                    data.append([
                        location,
                        zg_rz_val[:2],  # ZG
                        zg_rz_val[2:],  # RZ
                        f"{ai:02d}",
                        f"{bi:02d}",
                        f"{ro:02d}"
                    ])
    
    if data:
        df = pd.DataFrame(data, columns=["location", "ZG", "RZ", "ai", "bi", "ro"])
        # Sort exactly as requested: ZG → RZ → ai → ro → bi
        df = df.sort_values(by=["ZG", "RZ", "ai", "ro", "bi"], ascending=True)
        return df
    return None

@app.route("/", methods=["GET", "POST"])
def index():
    global all_zones
    message = ""
    show_visualization = False
    clear_form = False

    if request.method == "POST":
        zg_rz = request.form.get("zg_rz", "").strip()
        ai_list = request.form.getlist("ai")
        bi_start_list = request.form.getlist("bi_start")
        bi_end_list = request.form.getlist("bi_end")
        ro_start_list = request.form.getlist("ro_start")
        ro_end_list = request.form.getlist("ro_end")

        if "save_zone" in request.form:
            if not zg_rz:
                message = "❌ Please enter ZG/RZ for the new zone."
            elif len(zg_rz) != 4:
                message = "❌ ZG/RZ must be exactly 4 digits."
            else:
                ai_dict = {}
                valid_entries = False
                
                for i in range(len(ai_list)):
                    ai_val = ai_list[i].strip()
                    if not ai_val:
                        continue  # skip empty AI inputs
                    
                    valid_entries = True
                    
                    # Handle AI range or single value
                    if "-" in ai_val:  # AI range
                        try:
                            start, end = map(int, ai_val.split("-"))
                            ai_range = list(range(start, end + 1))
                        except ValueError:
                            message = "❌ Invalid AI range format. Use format like '1-3'."
                            break
                    else:  # Single AI value
                        try:
                            ai_range = [int(ai_val)]
                        except ValueError:
                            message = "❌ AI must be a number or range."
                            break

                    # Get BI and RO values
                    try:
                        bi_start = int(bi_start_list[i])
                        bi_end = int(bi_end_list[i])
                        ro_start = int(ro_start_list[i])
                        ro_end = int(ro_end_list[i])
                    except (ValueError, IndexError):
                        message = "❌ BI and RO values must be numbers."
                        break

                    # Store in dictionary
                    for ai in ai_range:
                        ai_dict[ai] = {
                            "bi": [bi_start, bi_end], 
                            "ro": [ro_start, ro_end]
                        }

                if not message and valid_entries:
                    all_zones.append({"zg_rz": zg_rz, "ai_dict": ai_dict})
                    message = f"✅ Zone {zg_rz} saved successfully! Click 'New Zone' to add another zone."
                    clear_form = True
                elif not valid_entries and not message:
                    message = "❌ Please add at least one AI range."

        elif "new_zone" in request.form:
            # Just clear the form fields
            clear_form = True
            message = "✅ Form cleared. You can now add a new zone."

        elif "download_excel" in request.form:
            if not all_zones:
                message = "❌ No zones to generate Excel. Please save zones first."
            else:
                try:
                    df = generate_locations_data()
                    if df is not None:
                        # Generate filename with timestamp
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"locations_{timestamp}.xlsx"
                        output_path = os.path.join(downloads_folder, filename)
                        df.to_excel(output_path, index=False)
                        
                        # Return the file for download
                        return send_file(
                            output_path,
                            as_attachment=True,
                            download_name=filename,
                            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )
                    else:
                        message = "❌ No data to generate Excel."
                        
                except Exception as e:
                    message = f"❌ Error generating Excel: {str(e)}"

        elif "download_text" in request.form:
            if not all_zones:
                message = "❌ No zones to generate text file. Please save zones first."
            else:
                try:
                    df = generate_locations_data()
                    if df is not None:
                        # Create tab-delimited text in memory
                        output = io.StringIO()
                        df.to_csv(output, sep='\t', index=False)
                        output.seek(0)
                        
                        # Generate filename with timestamp
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"locations_{timestamp}.txt"
                        
                        # Return the file for download
                        return send_file(
                            io.BytesIO(output.getvalue().encode('utf-8')),
                            as_attachment=True,
                            download_name=filename,
                            mimetype='text/plain'
                        )
                    else:
                        message = "❌ No data to generate text file."
                        
                except Exception as e:
                    message = f"❌ Error generating text file: {str(e)}"

        elif "visualize_zones" in request.form:
            if not all_zones:
                message = "❌ No zones to visualize. Please save zones first."
            else:
                message = "✅ Zones visualized below."
                show_visualization = True

        elif "clear_zones" in request.form:
            all_zones.clear()
            message = "✅ All zones cleared successfully!"

    return render_template("index.html", 
                         all_zones=all_zones, 
                         message=message, 
                         show_visualization=show_visualization,
                         clear_form=clear_form)

if __name__ == "__main__":
    app.run(debug=True)
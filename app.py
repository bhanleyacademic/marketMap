from flask import Flask, render_template, jsonify
import altair as alt
import pandas as pd
import numpy as np
import subprocess

# Initialize the Flask app
app = Flask(__name__)

# Load your data
file_path = 'data/profit.csv'
df = pd.read_csv(file_path)

# Get the number of unique skill tiers for consistent use in all templates
unique_skill_tiers = df['Skill Tier Name'].unique()
url_safe_skill_tiers = [st.lower().replace(" ", "_").replace("/", "_") for st in unique_skill_tiers]
num_skill_tiers = len(unique_skill_tiers)
# Create a list of tuples (skill_tier, url_safe_name)
skill_tier_links = list(zip(unique_skill_tiers, url_safe_skill_tiers))

# Function to format the cost
def format_cost(cost):
    # Check if the cost is already a string in the format 'Xg Ys Zc'
    if isinstance(cost, str) and 'g' in cost and 's' in cost and 'c' in cost:
        return cost

    # Convert the cost to a float
    cost = float(cost)

    # Format the cost to 4 decimal places
    formatted_cost = f"{cost:.4f}"

    # Split the cost into gold, silver, and copper
    gold = int(float(formatted_cost))
    silver = int((float(formatted_cost) * 100) % 100)
    copper = int((float(formatted_cost) * 10000) % 100)

    # Format gold with commas
    gold_str = f"{gold:,}"

    # Format silver and copper with leading zeros
    silver_str = f"{silver:02}"
    copper_str = f"{copper:02}"

    return f"{gold_str}g {silver_str}s {copper_str}c"

# Function to generate hex positions and chart
def create_heatmap(df_subset, title):
    base_hex_radius = 20
    x_offset = base_hex_radius * np.sqrt(3)# * 0.9
    y_offset = base_hex_radius * 1.5# * 0.9

    num_points = len(df_subset)
    num_columns = max(10, int(np.sqrt(num_points)))

    num_rows = (num_points + num_columns - 1) // num_columns
    x_positions = []
    y_positions = []
    for row in range(num_rows):
        for col in range(num_columns):
            if len(x_positions) < num_points:
                x = col * x_offset
                if row % 2 == 1:
                    x += x_offset / 2
                y = row * y_offset
                x_positions.append(x)
                y_positions.append(y)

    df_subset['x_pos'] = x_positions
    df_subset['y_pos'] = y_positions
    df_subset['Recipe Cost']=df_subset['Recipe Cost'].apply(format_cost)
    df_subset['Sale Price']=df_subset['Sale Price'].apply(format_cost)
    df_subset['Total Profit']=df_subset['Profit'].apply(format_cost)

    hexagon = "M0,-1L0.866,-0.5L0.866,0.5L0,1L-0.866,0.5L-0.866,-0.5Z"
    chart = alt.Chart(df_subset).mark_point(size=base_hex_radius**2, shape=hexagon).encode(
        x=alt.X('x_pos:Q', axis=None),
        y=alt.Y('y_pos:Q', axis=None),
        stroke=alt.value('black'),
        strokeWidth=alt.value(0.2),
        fill=alt.Fill('Profit:Q', scale=alt.Scale(scheme='viridis', type='log')),
        tooltip=[alt.Tooltip('Recipe Name:N'), alt.Tooltip('Recipe Cost:N'), alt.Tooltip('Sale Price:N'), alt.Tooltip('Total Profit:N')]
    ).properties(
        title=title,
        width=num_columns*(base_hex_radius/2)+100,
        height=num_rows*(base_hex_radius/2)+100
    ).configure_view(
        strokeWidth=0
    )
    return chart.to_json()

def test():
    return "Hello, World!"

# Route for the home page
@app.route("/")
def index():
    return render_template("index.html", num_skill_tiers=num_skill_tiers, unique_skill_tiers=unique_skill_tiers, skill_tier_links=skill_tier_links)

# Route for running an external script
# @app.route('/run-script', methods=['POST'])
# def run_script():
#     try:
#         result = subprocess.run(['python', 'your_script.py'], capture_output=True, text=True)
#         return jsonify({'output': result.stdout})
#     except Exception as e:
#         return jsonify({'error': str(e)})

# Route for running an included script
@app.route('/', methods=['POST'])
def run_script():
    try:
        output = test()
        return jsonify({'output': output})
    except Exception as e:
        return jsonify({'error': str(e)})

max_points = []
for i in unique_skill_tiers:
    df_subset = df[df['Skill Tier Name'] == i].reset_index(drop=True)
    df_subset = df_subset[df_subset['Profit'] > 0].reset_index(drop=True)
    num_profitable_recipes = len(df_subset)
    max_points.append(num_profitable_recipes)

# Loop through each skill tier and create unique routes
for i, (skill_tier, safe_name) in enumerate(zip(unique_skill_tiers, url_safe_skill_tiers)):
    df_subset = df[df['Skill Tier Name'] == skill_tier].reset_index(drop=True)
    #print(len(df_subset))
    df_subset = df_subset[df_subset['Profit'] > 0].reset_index(drop=True)
    #print(len(df_subset))
    chart_json = create_heatmap(df_subset, f"{skill_tier}")
    num_profitable_recipes = len(df_subset)
    max_value = max(max_points)
    # print(num_profitable_recipes)

    # Create a unique route function for each heatmap
    def make_route(chart_json=chart_json, skill_tier=skill_tier, num_profitable_recipes=num_profitable_recipes, max_value=max_value):
        return render_template("heatmap.html", chart_json=chart_json, title=skill_tier, num_skill_tiers=num_skill_tiers, skill_tier_links=skill_tier_links, num_profitable_recipes=num_profitable_recipes, max_value=max_value)

    # Add the route to the app with a unique endpoint
    clean_page_name = skill_tier.lower().replace(" ", "_").replace("/", "_")
    app.add_url_rule(f"/heatmap_{clean_page_name}", f"heatmap_page_{clean_page_name}", make_route)
print(max(max_points))
# Run the app
if __name__ == "__main__":
    app.run(debug=True)

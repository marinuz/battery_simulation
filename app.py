from flask import Flask, request, jsonify, render_template_string
import pandas as pd
from datetime import datetime

app = Flask(__name__)

# Load the dataset
file_path = './data/energieprijzen.csv'
data = pd.read_csv(file_path)
data['datumtijd'] = pd.to_datetime(data['datumtijd'])
data['Inkoop prijs per kWh'] = data['Inkoop prijs per kWh'].str.replace(',', '.').astype(float)

@app.route('/')
def index():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Batterij Simulatie</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            .chart-container {
                width: 100%;
                height: 400px;
            }
            .chart-timeline {
                width: 100%;
                height: 600px;
            }
        </style>
    </head>
    <body>
        <h1>Batterij Simulatie</h1>
        <p>Deze tool simuleert de winst die kan worden behaald door een batterij op te laden tijdens goedkope uren en te ontladen tijdens dure uren op de dynamische energiemarkt.</p>
        <form id="simulationForm">
            <label for="chargePower">Laadvermogen (kW):</label>
            <input type="number" id="chargePower" name="chargePower" step="0.1" value="2.2" required><br>
            <label for="dischargePower">Ontlaadvermogen (kW):</label>
            <input type="number" id="dischargePower" name="dischargePower" step="0.1" value="1.7" required><br>
            <label for="batteryCapacity">Batterijcapaciteit (kWh):</label>
            <input type="number" id="batteryCapacity" name="batteryCapacity" step="0.1" value="5" required><br>
            <label for="chargeEfficiency">Laadrendement (%):</label>
            <input type="number" id="chargeEfficiency" name="chargeEfficiency" step="0.1" value="95" required><br>
            <label for="dischargeEfficiency">Ontlaadrendement (%):</label>
            <input type="number" id="dischargeEfficiency" name="dischargeEfficiency" step="0.1" value="95" required><br>
            <label for="maxDischarges">Maximaal aantal ontladingen per dag:</label>
            <input type="number" id="maxDischarges" name="maxDischarges" step="1" value="5" required><br>
            <label for="year">Selecteer jaar:</label>
            <select id="year" name="year" required></select><br>
            <label for="includeTax">Inclusief energiebelasting:</label>
            <input type="checkbox" id="includeTax" name="includeTax"><br>
            <button type="submit">Simuleer</button>
        </form>
        <h2>Simulatie Resultaten</h2>
        <div id="result"></div>
        <div class="chart-container">
            <canvas id="profitChart"></canvas>
        </div>
        <div class="chart-container">
            <canvas id="dischargeChart"></canvas>
        </div>
        <div class="chart-timeline">
            <canvas id="timelineChart"></canvas>
        </div>
        <div class="chart-container">
            <canvas id="priceDifferenceChart"></canvas>
        </div>

        <script>
            // Populate year dropdown
            let currentYear = new Date().getFullYear();
            let startYear = 2013; // Based on data
            let yearSelect = document.getElementById('year');
            for (let year = startYear; year <= currentYear; year++) {
                let option = document.createElement('option');
                option.value = year;
                option.textContent = year;
                yearSelect.appendChild(option);
            }

            let profitChart = null;
            let dischargeChart = null;
            let timelineChart = null;
            let priceDifferenceChart = null;

            document.getElementById('simulationForm').addEventListener('submit', function(event) {
                event.preventDefault();
                let formData = new FormData(event.target);
                let params = new URLSearchParams(formData).toString();
                
                fetch('/simulate?' + params)
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('result').innerText = 'Totale Winst: €' + data.profit.toFixed(2) + '\\nTotaal aantal ontladingen: ' + data.totalDischarges;

                        if (profitChart) {
                            profitChart.destroy();
                        }
                        if (dischargeChart) {
                            dischargeChart.destroy();
                        }
                        if (timelineChart) {
                            timelineChart.destroy();
                        }
                        if (priceDifferenceChart) {
                            priceDifferenceChart.destroy();
                        }

                        const profitCtx = document.getElementById('profitChart').getContext('2d');
                        profitChart = new Chart(profitCtx, {
                            type: 'line',
                            data: {
                                labels: Array.from({length: data.dailyProfits.length}, (_, i) => i + 1),
                                datasets: [{
                                    label: 'Dagelijkse Winst (€)',
                                    data: data.dailyProfits,
                                    borderColor: 'rgba(75, 192, 192, 1)',
                                    borderWidth: 1,
                                    fill: false
                                }]
                            },
                            options: {
                                scales: {
                                    x: {
                                        beginAtZero: true,
                                        title: {
                                            display: true,
                                            text: 'Dag van het Jaar'
                                        }
                                    },
                                    y: {
                                        beginAtZero: true,
                                        title: {
                                            display: true,
                                            text: 'Winst (€)'
                                        }
                                    }
                                }
                            }
                        });

                        const dischargeCtx = document.getElementById('dischargeChart').getContext('2d');
                        dischargeChart = new Chart(dischargeCtx, {
                            type: 'line',
                            data: {
                                labels: Array.from({length: data.dailyDischarges.length}, (_, i) => i + 1),
                                datasets: [{
                                    label: 'Dagelijkse Ontladingen',
                                    data: data.dailyDischarges,
                                    borderColor: 'rgba(153, 102, 255, 1)',
                                    borderWidth: 1,
                                    fill: false
                                }]
                            },
                            options: {
                                scales: {
                                    x: {
                                        beginAtZero: true,
                                        title: {
                                            display: true,
                                            text: 'Dag van het Jaar'
                                        }
                                    },
                                    y: {
                                        beginAtZero: true,
                                        title: {
                                            display: true,
                                            text: 'Aantal Ontladingen'
                                        }
                                    }
                                }
                            }
                        });

                        const timelineCtx = document.getElementById('timelineChart').getContext('2d');
                        timelineChart = new Chart(timelineCtx, {
                            type: 'bubble',
                            data: {
                                datasets: [{
                                    label: 'Ontladen',
                                    data: data.dischargeTimes,
                                    backgroundColor: 'rgba(153, 102, 255, 1)',
                                }, {
                                    label: 'Laden',
                                    data: data.chargeTimes,
                                    backgroundColor: 'rgba(75, 192, 192, 1)',
                                }]
                            },
                            options: {
                                scales: {
                                    x: {
                                        type: 'linear',
                                        position: 'bottom',
                                        title: {
                                            display: true,
                                            text: 'Dag van de Week'
                                        },
                                        ticks: {
                                            callback: function(value) {
                                                const days = ['Zondag', 'Maandag', 'Dinsdag', 'Woensdag', 'Donderdag', 'Vrijdag', 'Zaterdag'];
                                                return days[value % 7];
                                            }
                                        }
                                    },
                                    y: {
                                        title: {
                                            display: true,
                                            text: 'Uur van de Dag'
                                        },
                                        ticks: {
                                            stepSize: 1,
                                            callback: function(value) {
                                                if (value % 1 === 0) {
                                                    return value + ':00';
                                                }
                                                return '';
                                            }
                                        }
                                    }
                                },
                                plugins: {
                                    tooltip: {
                                        callbacks: {
                                            label: function(context) {
                                                return context.raw.label + ': ' + context.raw.size + ' keer';
                                            }
                                        }
                                    }
                                }
                            }
                        });

                        const priceDifferenceCtx = document.getElementById('priceDifferenceChart').getContext('2d');
                        priceDifferenceChart = new Chart(priceDifferenceCtx, {
                            type: 'line',
                            data: {
                                labels: data.priceDifferences.map((_, index) => index + 1),
                                datasets: [{
                                    label: 'Prijsverschillen (€)',
                                    data: data.priceDifferences,
                                    borderColor: 'rgba(255, 99, 132, 1)',
                                    borderWidth: 1,
                                    fill: false
                                }]
                            },
                            options: {
                                scales: {
                                    x: {
                                        beginAtZero: true,
                                        title: {
                                            display: true,
                                            text: 'Handelingen'
                                        }
                                    },
                                    y: {
                                        beginAtZero: true,
                                        title: {
                                            display: true,
                                            text: 'Prijsverschil (€)'
                                        }
                                    }
                                }
                            }
                        });
                    })
                    .catch(error => console.error('Error:', error));
            });
        </script>
    </body>
    </html>
    """
    return render_template_string(html_content)

@app.route('/simulate')
def simulate():
    charge_power = float(request.args.get('chargePower'))
    discharge_power = float(request.args.get('dischargePower'))
    battery_capacity = float(request.args.get('batteryCapacity'))
    charge_efficiency = float(request.args.get('chargeEfficiency')) / 100
    discharge_efficiency = float(request.args.get('dischargeEfficiency')) / 100
    max_discharges = int(request.args.get('maxDischarges'))
    year = int(request.args.get('year'))
    include_tax = request.args.get('includeTax') == 'on'
    
    # Filter data for the selected year
    data_year = data[data['datumtijd'].dt.year == year]

    battery_state = 0  # Initial battery state in kWh
    daily_profits = []
    daily_discharge_counts = []
    total_discharges = 0
    charge_times = []
    discharge_times = []
    price_differences = []
    
    data_year.loc[:, 'date'] = data_year['datumtijd'].dt.date
    daily_data = data_year.groupby('date')

    charge_counts = {}
    discharge_counts = {}
    
    for date, group in daily_data:
        group = group.sort_values('Inkoop prijs per kWh')
        daily_profit = 0
        daily_discharges = 0
        
        # Apply tax if included
        if include_tax:
            group['Inkoop prijs per kWh'] = group['Inkoop prijs per kWh'] + 0.13
            group['Inkoop prijs per kWh'] = group['Inkoop prijs per kWh'] * 1.21
        
        # Charge during the cheapest hours
        for _, row in group.iterrows():
            price = row['Inkoop prijs per kWh']
            if battery_state < battery_capacity:
                charge_amount = min(charge_power * charge_efficiency, battery_capacity - battery_state)
                battery_state += charge_amount
                daily_profit -= charge_amount * price
                time_key = (row['datumtijd'].dayofweek, row['datumtijd'].hour)
                if time_key in charge_counts:
                    charge_counts[time_key] += 1
                else:
                    charge_counts[time_key] = 1
        
        # Discharge during the most expensive hours, limited by max discharges
        group = group.sort_values('Inkoop prijs per kWh', ascending=False)
        for _, row in group.iterrows():
            if daily_discharges >= max_discharges:
                break
            price = row['Inkoop prijs per kWh']
            if battery_state > 0:
                discharge_amount = min(discharge_power / discharge_efficiency, battery_state)
                battery_state -= discharge_amount
                daily_profit += discharge_amount * price * discharge_efficiency
                daily_discharges += 1
                time_key = (row['datumtijd'].dayofweek, row['datumtijd'].hour)
                if time_key in discharge_counts:
                    discharge_counts[time_key] += 1
                else:
                    discharge_counts[time_key] = 1
                price_differences.append(price - row['Inkoop prijs per kWh'])
        
        daily_profits.append(daily_profit)
        daily_discharge_counts.append(daily_discharges)
        total_discharges += daily_discharges
    
    # Prepare data for plotting
    charge_times = [{'x': k[0], 'y': k[1], 'r': v, 'label': 'Laden'} for k, v in charge_counts.items()]
    discharge_times = [{'x': k[0], 'y': k[1], 'r': v, 'label': 'Ontladen'} for k, v in discharge_counts.items()]
    
    return jsonify({
        'profit': sum(daily_profits),
        'dailyProfits': daily_profits,
        'dailyDischarges': daily_discharge_counts,
        'totalDischarges': total_discharges,
        'chargeTimes': charge_times,
        'dischargeTimes': discharge_times,
        'priceDifferences': price_differences
    })

if __name__ == '__main__':
    app.run(debug=True)

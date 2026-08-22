
let marketChart = null;
let rawPredictionHistory = [];


async function initAnalyticsDashboard() {
    try {
        
        const response = await fetch('/analytics/history');
        rawPredictionHistory = await response.json();

        populateDropdownFilters(rawPredictionHistory);


        applyFiltersAndRender();
    } catch (error) {
        console.error("History fetch problem:", error);
    }
}


function populateDropdownFilters(historyData) {
    const mandiSelect = document.getElementById("mandiFilter");
    const cropSelect = document.getElementById("cropFilter");

    
    const uniqueMandis = [...new Set(historyData.map(item => item.mandi))];
    const uniqueCrops = [...new Set(historyData.map(item => item.item))];

    uniqueMandis.forEach(mandi => {
        const option = document.createElement("option");
        option.value = mandi;
        option.textContent = mandi.toUpperCase(); 
        mandiSelect.appendChild(option);
    });


    uniqueCrops.forEach(crop => {
        const option = document.createElement("option");
        option.value = crop;
        option.textContent = crop.toUpperCase();
        cropSelect.appendChild(option);
    });
}





















// Filter mechanism aur Chart Rendering
function applyFiltersAndRender() {
    const selectedMandi = document.getElementById("mandiFilter").value;
    const selectedCrop = document.getElementById("cropFilter").value;

    // 1. Data Filtering
    const filteredData = rawPredictionHistory.filter(record => {
        const matchesMandi = (selectedMandi === "all") || (record.mandi === selectedMandi);
        const matchesCrop = (selectedCrop === "all") || (record.item === selectedCrop);
        return matchesMandi && matchesCrop;
    });

    // 2. Arrays extract karna Chart.js ke liye
    const labels = filteredData.map(d => d.timestamp); // X-Axis (Time)
    const wholesalePrices = filteredData.map(d => d.wholesale_base_price);
    const retailPrices = filteredData.map(d => d.predicted_retail_price_pkr);
    const distances = filteredData.map(d => d.avg_distance_km);

    // 3. Purana Chart Destroy karna (Glitch-free re-render ke liye)
    if (marketChart) {
        marketChart.destroy();
    }

    // 4. Chart.js Instance Banana
    const ctx = document.getElementById("marketTrendChart").getContext("2d");
    marketChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Wholesale Price (PKR)',
                    data: wholesalePrices,
                    borderColor: '#2196F3', // Blue line
                    backgroundColor: 'rgba(33, 150, 243, 0.1)',
                    fill: true,
                    tension: 0.3
                },
                {
                    label: 'Predicted Retail Price (PKR)',
                    data: retailPrices,
                    borderColor: '#4CAF50', // Green line
                    backgroundColor: 'rgba(76, 175, 80, 0.1)',
                    fill: true,
                    tension: 0.3
                },
                {
                    label: 'Distance (KM)',
                    data: distances,
                    borderColor: '#FF9800', // Orange line
                    borderDash: [5, 5], // Dashed line for distance
                    tension: 0.1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: '7-Day Price Trends & Logistics Distance Factor'
                }
            },
            scales: {
                x: {
                    title: { display: true, text: 'Date & Time' }
                },
                y: {
                    title: { display: true, text: 'Value / Price (PKR / KM)' },
                    beginAtZero: false
                }
            }
        }
    });
}

// Window load hone par init script chalana
document.addEventListener("DOMContentLoaded", initAnalyticsDashboard);

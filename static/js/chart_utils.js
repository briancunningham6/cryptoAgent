/**
 * Chart utility functions for the crypto AI agent application
 * Uses Chart.js library for rendering charts
 */

// Default chart colors (with transparency)
const chartColors = {
    primary: 'rgba(13, 110, 253, 0.8)',
    primaryLight: 'rgba(13, 110, 253, 0.2)',
    success: 'rgba(40, 167, 69, 0.8)',
    successLight: 'rgba(40, 167, 69, 0.2)',
    danger: 'rgba(220, 53, 69, 0.8)',
    dangerLight: 'rgba(220, 53, 69, 0.2)',
    warning: 'rgba(255, 193, 7, 0.8)',
    warningLight: 'rgba(255, 193, 7, 0.2)',
    info: 'rgba(23, 162, 184, 0.8)',
    infoLight: 'rgba(23, 162, 184, 0.2)',
    secondary: 'rgba(108, 117, 125, 0.8)',
    secondaryLight: 'rgba(108, 117, 125, 0.2)',
};

// Chart.js default configuration
const defaultChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            labels: {
                color: '#e0e0e0'
            }
        },
        tooltip: {
            backgroundColor: 'rgba(50, 50, 50, 0.9)',
            titleColor: '#ffffff',
            bodyColor: '#ffffff',
            borderColor: 'rgba(255, 255, 255, 0.2)',
            borderWidth: 1
        }
    },
    scales: {
        x: {
            grid: {
                color: 'rgba(255, 255, 255, 0.1)'
            },
            ticks: {
                color: '#aaaaaa'
            }
        },
        y: {
            grid: {
                color: 'rgba(255, 255, 255, 0.1)'
            },
            ticks: {
                color: '#aaaaaa'
            }
        }
    }
};

// Function to create a price history chart
function createPriceHistoryChart(canvasId, priceData, timeLabels) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: timeLabels,
            datasets: [{
                label: 'Price',
                data: priceData,
                borderColor: chartColors.primary,
                backgroundColor: chartColors.primaryLight,
                borderWidth: 2,
                tension: 0.2,
                fill: true,
                pointRadius: 0,
                pointHoverRadius: 3
            }]
        },
        options: {
            ...defaultChartOptions,
            plugins: {
                ...defaultChartOptions.plugins,
                tooltip: {
                    ...defaultChartOptions.plugins.tooltip,
                    callbacks: {
                        label: function(context) {
                            return `Price: ${context.parsed.y.toFixed(4)}`;
                        }
                    }
                }
            }
        }
    });
}

// Function to create a profit/loss chart
function createProfitLossChart(canvasId, profitLossData, tradeLabels) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    // Split into profits and losses for coloring
    const colors = profitLossData.map(value => value >= 0 ? chartColors.success : chartColors.danger);
    const backgroundColors = profitLossData.map(value => value >= 0 ? chartColors.successLight : chartColors.dangerLight);
    
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: tradeLabels,
            datasets: [{
                label: 'Profit/Loss (%)',
                data: profitLossData,
                backgroundColor: backgroundColors,
                borderColor: colors,
                borderWidth: 1
            }]
        },
        options: {
            ...defaultChartOptions,
            scales: {
                ...defaultChartOptions.scales,
                y: {
                    ...defaultChartOptions.scales.y,
                    beginAtZero: false
                }
            }
        }
    });
}

// Function to create a cumulative profit/loss chart
function createCumulativeProfitLossChart(canvasId, profitLossData, tradeLabels) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    // Calculate cumulative P/L
    let cumulativeData = [];
    let cumulativeValue = 0;
    
    profitLossData.forEach(value => {
        cumulativeValue += value;
        cumulativeData.push(cumulativeValue);
    });
    
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: tradeLabels,
            datasets: [{
                label: 'Cumulative P/L (%)',
                data: cumulativeData,
                borderColor: chartColors.info,
                backgroundColor: chartColors.infoLight,
                borderWidth: 2,
                tension: 0.1,
                fill: true
            }]
        },
        options: defaultChartOptions
    });
}

// Function to create a market trend summary chart (pie chart)
function createMarketTrendChart(canvasId, uptrends, downtrends, sideways) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    return new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['Uptrend', 'Downtrend', 'Sideways'],
            datasets: [{
                data: [uptrends, downtrends, sideways],
                backgroundColor: [
                    chartColors.success,
                    chartColors.danger,
                    chartColors.warning
                ],
                borderWidth: 1,
                borderColor: '#333'
            }]
        },
        options: {
            ...defaultChartOptions,
            plugins: {
                ...defaultChartOptions.plugins,
                legend: {
                    ...defaultChartOptions.plugins.legend,
                    position: 'bottom'
                }
            }
        }
    });
}

// Function to create a volatility comparison chart
function createVolatilityChart(canvasId, pairNames, volatilityValues) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    // Generate colors based on volatility values
    const colors = volatilityValues.map(value => {
        if (value < 10) return chartColors.success;
        if (value < 20) return chartColors.warning;
        return chartColors.danger;
    });
    
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: pairNames,
            datasets: [{
                label: 'Volatility (%)',
                data: volatilityValues,
                backgroundColor: colors,
                borderColor: colors.map(color => color.replace('0.8', '1')),
                borderWidth: 1
            }]
        },
        options: {
            ...defaultChartOptions,
            indexAxis: 'y',
            plugins: {
                ...defaultChartOptions.plugins,
                legend: {
                    display: false
                }
            }
        }
    });
}

// Function to create a trader performance comparison chart
function createTraderPerformanceChart(canvasId, traderNames, successRates, avgProfits) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: traderNames,
            datasets: [
                {
                    label: 'Success Rate (%)',
                    data: successRates,
                    backgroundColor: chartColors.primary,
                    borderColor: chartColors.primary.replace('0.8', '1'),
                    borderWidth: 1,
                    yAxisID: 'y'
                },
                {
                    label: 'Avg. Profit (%)',
                    data: avgProfits,
                    backgroundColor: chartColors.success,
                    borderColor: chartColors.success.replace('0.8', '1'),
                    borderWidth: 1,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            ...defaultChartOptions,
            scales: {
                ...defaultChartOptions.scales,
                y: {
                    ...defaultChartOptions.scales.y,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Success Rate (%)',
                        color: '#aaaaaa'
                    }
                },
                y1: {
                    position: 'right',
                    grid: {
                        drawOnChartArea: false,
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#aaaaaa'
                    },
                    title: {
                        display: true,
                        text: 'Avg. Profit (%)',
                        color: '#aaaaaa'
                    }
                }
            }
        }
    });
}

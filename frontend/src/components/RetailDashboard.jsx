import React, { useState, useEffect } from 'react';
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const Dashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        console.log("Fetching data from API...");
        const response = await fetch('http://localhost:8000/api/dashboard/data');
        console.log("API response status:", response.status);
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        const jsonData = await response.json();
        console.log("Received data:", jsonData);
        setData(jsonData);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching data:', err);
        setError(`Failed to fetch dashboard data: ${err.message}`);
        setLoading(false);
        
        // Comment this out to see the error state instead of falling back to mock data
        // setData(mockData);
      }
    };
    
    fetchData();
  }, []);

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        height: '100vh', 
        alignItems: 'center', 
        justifyContent: 'center' 
      }}>
        <div style={{ 
          fontSize: '1.25rem', 
          fontWeight: 600 
        }}>
          Loading dashboard data...
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div style={{ 
        display: 'flex', 
        height: '100vh', 
        alignItems: 'center', 
        justifyContent: 'center' 
      }}>
        <div style={{ 
          fontSize: '1.25rem', 
          fontWeight: 600, 
          color: '#ef4444' 
        }}>
          {error}
        </div>
      </div>
    );
  }

  return (
    <div style={{ 
      minHeight: '100vh', 
      backgroundColor: '#f3f4f6' 
    }}>
      <header style={{ 
        backgroundColor: '#ffffff', 
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)' 
      }}>
        <div style={{ 
          maxWidth: '80rem', 
          margin: '0 auto', 
          padding: '1.5rem 1rem' 
        }}>
          <h1 style={{ 
            fontSize: '1.875rem', 
            fontWeight: 'bold', 
            color: '#111827' 
          }}>
            Retail Dashboard
          </h1>
        </div>
      </header>
      <main style={{ 
        maxWidth: '80rem', 
        margin: '0 auto', 
        padding: '1.5rem 1rem' 
      }}>
        <KpiSection data={data.kpis} />
        <div style={{ 
          marginTop: '1.5rem', 
          display: 'grid', 
          gridTemplateColumns: '1fr', 
          gap: '1.5rem'
        }}>
          <SalesTrends data={data.salesTrends} />
          <ProductPerformance data={data.productPerformance} />
        </div>
        <div style={{ 
          marginTop: '1.5rem', 
          display: 'grid', 
          gridTemplateColumns: '1fr', 
          gap: '1.5rem'
        }}>
          <InventorySummary data={data.inventorySummary} />
          <AlertsPanel alerts={data.alerts} />
        </div>
      </main>
    </div>
  );
};

const KpiSection = ({ data }) => {
  const formatNumber = (num) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(num);
  };

  const getChangeColor = (change) => {
    return change >= 0 ? '#10b981' : '#ef4444';
  };

  const getChangeArrow = (change) => {
    return change >= 0 ? '↑' : '↓';
  };

  return (
    <div style={{ 
      display: 'grid', 
      gridTemplateColumns: '1fr', 
      gap: '1.25rem'
    }}>
      <KpiCard 
        title="Revenue" 
        value={formatNumber(data.revenue)} 
        change={data.revenueChange} 
        changeLabel="vs last period" 
      />
      <KpiCard 
        title="Orders" 
        value={data.orders.toLocaleString()} 
        change={data.ordersChange} 
        changeLabel="vs last period" 
      />
      <KpiCard 
        title="Conversion Rate" 
        value={`${data.conversionRate.toFixed(1)}%`} 
        change={data.conversionRateChange} 
        changeLabel="vs last period" 
      />
      <KpiCard 
        title="Inventory Count" 
        value={data.inventoryCount.toLocaleString()} 
        change={data.inventoryCountChange} 
        changeLabel="vs last period" 
      />
    </div>
  );
};

const KpiCard = ({ title, value, change, changeLabel }) => {
  const getChangeColor = (change) => {
    return change >= 0 ? '#10b981' : '#ef4444';
  };

  const getChangeArrow = (change) => {
    return change >= 0 ? '↑' : '↓';
  };

  return (
    <div style={{ 
      overflow: 'hidden', 
      borderRadius: '0.5rem', 
      backgroundColor: '#ffffff', 
      boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)' 
    }}>
      <div style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <div style={{ flexShrink: 0 }}>
            <h3 style={{ 
              fontSize: '1.125rem', 
              fontWeight: 500, 
              color: '#111827' 
            }}>
              {title}
            </h3>
          </div>
        </div>
        <div style={{ marginTop: '0.75rem' }}>
          <p style={{ 
            fontSize: '1.875rem', 
            fontWeight: 'bold', 
            color: '#111827' 
          }}>
            {value}
          </p>
          <p style={{ 
            marginTop: '0.25rem', 
            display: 'flex', 
            alignItems: 'baseline', 
            fontSize: '0.875rem', 
            color: getChangeColor(change)
          }}>
            <span style={{ fontWeight: 600 }}>
              {getChangeArrow(change)} {Math.abs(change)}%
            </span>
            <span style={{ 
              marginLeft: '0.25rem', 
              color: '#6b7280' 
            }}>
              {changeLabel}
            </span>
          </p>
        </div>
      </div>
    </div>
  );
};

const SalesTrends = ({ data }) => {
  // Format date for display on chart
  const formattedData = data.dailySales.map(item => ({
    ...item,
    formattedDate: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }));

  return (
    <div style={{ 
      overflow: 'hidden', 
      borderRadius: '0.5rem', 
      backgroundColor: '#ffffff', 
      boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)' 
    }}>
      <div style={{ padding: '1.5rem' }}>
        <h3 style={{ 
          fontSize: '1.125rem', 
          fontWeight: 500, 
          color: '#111827' 
        }}>
          Sales Trends (Last 30 Days)
        </h3>
        <div style={{ 
          marginTop: '1rem', 
          height: '18rem' 
        }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={formattedData} margin={{ top: 10, right: 10, left: 10, bottom: 30 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis 
                dataKey="formattedDate" 
                angle={-45}
                textAnchor="end"
                height={70}
                tick={{ fontSize: 12 }}
                tickFormatter={(value, index) => index % 3 === 0 ? value : ''}
              />
              <YAxis 
                yAxisId="left"
                tickFormatter={(value) => `$${value.toLocaleString()}`}
              />
              <YAxis 
                yAxisId="right" 
                orientation="right"
                tickFormatter={(value) => `${value.toLocaleString()}`}
              />
              <Tooltip 
                formatter={(value, name) => {
                  if (name === "revenue") return [`$${value.toLocaleString()}`, "Revenue"];
                  return [value.toLocaleString(), "Orders"];
                }}
                labelFormatter={(label) => `Date: ${label}`}
              />
              <Legend />
              <Line 
                yAxisId="left" 
                type="monotone" 
                dataKey="revenue" 
                name="Revenue" 
                stroke="#3b82f6" 
                strokeWidth={2} 
                dot={false} 
                activeDot={{ r: 6 }} 
              />
              <Line 
                yAxisId="right" 
                type="monotone" 
                dataKey="orders" 
                name="Orders" 
                stroke="#10b981" 
                strokeWidth={2} 
                dot={false} 
                activeDot={{ r: 6 }} 
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

const ProductPerformance = ({ data }) => {
  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

  return (
    <div style={{ 
      overflow: 'hidden', 
      borderRadius: '0.5rem', 
      backgroundColor: '#ffffff', 
      boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)' 
    }}>
      <div style={{ padding: '1.5rem' }}>
        <h3 style={{ 
          fontSize: '1.125rem', 
          fontWeight: 500, 
          color: '#111827' 
        }}>
          Top Products
        </h3>
        <div style={{ 
          marginTop: '1rem', 
          height: '18rem' 
        }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data.topProducts}
              layout="vertical"
              margin={{
                top: 10,
                right: 30,
                left: 60,
                bottom: 10,
              }}
            >
              <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
              <XAxis type="number" />
              <YAxis dataKey="name" type="category" width={90} />
              <Tooltip formatter={(value) => [`${value.toLocaleString()} units`, "Sales"]} />
              <Bar dataKey="sales" name="Units Sold">
                {data.topProducts.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

const InventorySummary = ({ data }) => {
  const COLORS = ['#ef4444', '#10b981', '#f59e0b'];
  
  const pieData = [
    { name: 'Low Stock', value: data.stockHealth.low_stock },
    { name: 'Healthy Stock', value: data.stockHealth.healthy_stock },
    { name: 'Overstock', value: data.stockHealth.overstock },
  ];

  return (
    <div style={{ 
      overflow: 'hidden', 
      borderRadius: '0.5rem', 
      backgroundColor: '#ffffff', 
      boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)' 
    }}>
      <div style={{ padding: '1.5rem' }}>
        <h3 style={{ 
          fontSize: '1.125rem', 
          fontWeight: 500, 
          color: '#111827' 
        }}>
          Inventory Summary
        </h3>
        <div style={{ 
          marginTop: '1rem', 
          display: 'grid', 
          gridTemplateColumns: '1fr', 
          gap: '1.5rem'
        }}>
          <div>
            <h4 style={{ 
              fontSize: '0.875rem', 
              fontWeight: 500, 
              color: '#6b7280' 
            }}>
              Stock Health
            </h4>
            <div style={{ 
              height: '12rem', 
              marginTop: '0.5rem' 
            }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={70}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => [`${value.toLocaleString()} items`, null]} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div>
            <h4 style={{ 
              fontSize: '0.875rem', 
              fontWeight: 500, 
              color: '#6b7280' 
            }}>
              Store Inventory
            </h4>
            <div style={{ 
              height: '12rem', 
              marginTop: '0.5rem' 
            }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={data.storeInventory}
                  margin={{
                    top: 10,
                    right: 10,
                    left: 10,
                    bottom: 20,
                  }}
                >
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis 
                    dataKey="store_id" 
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => `Store ${value}`}
                  />
                  <YAxis 
                    tickFormatter={(value) => `${value.toLocaleString()}`}
                  />
                  <Tooltip
                    formatter={(value) => [`${value.toLocaleString()} units`, "Total Stock"]}
                    labelFormatter={(value) => `Store ${value}`}
                  />
                  <Bar dataKey="total_stock" name="Total Stock" fill="#3b82f6" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const AlertsPanel = ({ alerts }) => {
  const getAlertStyles = (type) => {
    switch (type) {
      case 'error':
        return {
          backgroundColor: '#fef2f2',
          color: '#991b1b',
          borderColor: '#fca5a5'
        };
      case 'warning':
        return {
          backgroundColor: '#fffbeb',
          color: '#92400e',
          borderColor: '#fcd34d'
        };
      case 'success':
        return {
          backgroundColor: '#ecfdf5',
          color: '#065f46',
          borderColor: '#6ee7b7'
        };
      default:
        return {
          backgroundColor: '#eff6ff',
          color: '#1e40af',
          borderColor: '#93c5fd'
        };
    }
  };

  const getAlertIcon = (type) => {
    switch (type) {
      case 'error':
        return '⚠️';
      case 'warning':
        return '⚠️';
      case 'success':
        return '✅';
      default:
        return 'ℹ️';
    }
  };

  return (
    <div style={{ 
      overflow: 'hidden', 
      borderRadius: '0.5rem', 
      backgroundColor: '#ffffff', 
      boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)' 
    }}>
      <div style={{ padding: '1.5rem' }}>
        <h3 style={{ 
          fontSize: '1.125rem', 
          fontWeight: 500, 
          color: '#111827' 
        }}>
          Recent Alerts
        </h3>
        <div style={{ 
          marginTop: '1rem', 
          display: 'flex', 
          flexDirection: 'column', 
          gap: '1rem',
          maxHeight: '18rem',
          overflowY: 'auto'
        }}>
          {alerts.map((alert, index) => {
            const alertStyle = getAlertStyles(alert.type);
            return (
              <div 
                key={index} 
                style={{ 
                  borderRadius: '0.375rem', 
                  border: '1px solid', 
                  padding: '1rem',
                  backgroundColor: alertStyle.backgroundColor,
                  color: alertStyle.color,
                  borderColor: alertStyle.borderColor
                }}
              >
                <div style={{ display: 'flex' }}>
                  <div style={{ 
                    flexShrink: 0, 
                    marginRight: '0.75rem' 
                  }}>
                    {getAlertIcon(alert.type)}
                  </div>
                  <div>
                    <h4 style={{ 
                      fontSize: '0.875rem', 
                      fontWeight: 500 
                    }}>
                      {alert.title}
                    </h4>
                    <div style={{ 
                      marginTop: '0.25rem', 
                      fontSize: '0.875rem' 
                    }}>
                      {alert.message}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

// Mock data for testing when API is not available
/*const mockData = {
  kpis: {
    revenue: 128750,
    revenueChange: 12.5,
    conversionRate: 3.2,
    conversionRateChange: 0.6,
    orders: 1250,
    ordersChange: 5.3,
    inventoryCount: 4580,
    inventoryCountChange: -2.1
  },
  salesTrends: {
    dailySales: Array.from({ length: 30 }, (_, i) => {
      const date = new Date();
      date.setDate(date.getDate() - (29 - i));
      
      // Higher sales on weekends
      const isWeekend = date.getDay() === 0 || date.getDay() === 6;
      const baseSales = 3000 + Math.random() * 1500;
      const sales = isWeekend ? baseSales * 1.4 : baseSales;
      
      return {
        date: date.toISOString().split('T')[0],
        revenue: sales,
        orders: Math.round(sales / 100)
      };
    })
  },
  inventorySummary: {
    stockHealth: {
      low_stock: 12,
      healthy_stock: 85,
      overstock: 23
    },
    storeInventory: [
      { store_id: 1, total_stock: 2240 },
      { store_id: 2, total_stock: 2340 }
    ]
  },
  productPerformance: {
    topProducts: [
      { name: "Product 12", sales: 156 },
      { name: "Product 5", sales: 129 },
      { name: "Product 8", sales: 107 },
      { name: "Product 15", sales: 92 },
      { name: "Product 3", sales: 76 }
    ]
  },
  alerts: [
    {
      type: "warning",
      title: "Low Stock Alert",
      message: "Product 5 is running low in Store #1 (3 units remaining)"
    },
    {
      type: "success",
      title: "Restock Approved",
      message: "Restock request for Product 2 at Store #1 was approved on 2023-04-01"
    },
    {
      type: "error",
      title: "Inventory Discrepancy",
      message: "Negative stock detected for 2 products in Store #2"
    }
  ]
};
*/
export default Dashboard;
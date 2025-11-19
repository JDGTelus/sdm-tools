"""React component code for bundled SPA."""

# This file contains all the React component JavaScript code
# that will be injected into the SPA bundle template

COMPONENT_CODE = r"""
      // ═══════════════════════════════════════════════════════════════════════
      // SHARED CHART COMPONENTS
      // ═══════════════════════════════════════════════════════════════════════
      
      const BarChart = ({ data, title }) => {
        const chartRef = useRef(null);
        const chartInstance = useRef(null);

        useEffect(() => {
          if (!chartRef.current || !data) return;
          if (chartInstance.current) chartInstance.current.destroy();

          const ctx = chartRef.current.getContext("2d");
          chartInstance.current = new Chart(ctx, {
            type: "bar",
            data: {
              labels: data.labels,
              datasets: data.datasets,
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: { position: "top" },
                title: { display: true, text: title, font: { size: 16 } },
              },
              scales: {
                x: { stacked: true },
                y: { stacked: true, beginAtZero: true },
              },
            },
          });

          return () => {
            if (chartInstance.current) chartInstance.current.destroy();
          };
        }, [data, title]);

        return <canvas ref={chartRef} className="w-full h-64"></canvas>;
      };

      const DoughnutChart = ({ data, title }) => {
        const chartRef = useRef(null);
        const chartInstance = useRef(null);

        useEffect(() => {
          if (!chartRef.current || !data) return;
          if (chartInstance.current) chartInstance.current.destroy();

          const ctx = chartRef.current.getContext("2d");
          chartInstance.current = new Chart(ctx, {
            type: "doughnut",
            data: {
              labels: data.labels,
              datasets: [
                {
                  data: data.values,
                  backgroundColor: ["#4B0082", "#EA580C", "#FF6B6B", "#FFE66D"],
                },
              ],
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: { position: "right" },
                title: { display: true, text: title, font: { size: 16 } },
              },
            },
          });

          return () => {
            if (chartInstance.current) chartInstance.current.destroy();
          };
        }, [data, title]);

        return <canvas ref={chartRef} className="w-full h-64"></canvas>;
      };

      // Developer color palette
      const DEVELOPER_COLORS = [
        '#4B0082', '#66CC00', '#0066CC', '#FF6B6B',
        '#FFB347', '#9B59B6', '#1ABC9C',
      ];

      const SPRINT_AVG_COLOR = '#FF0000';
      const OVERALL_AVG_COLOR = '#000000';

      const LineChart = ({ data, title, metricType, fullSprintData }) => {
        const chartRef = useRef(null);
        const chartInstance = useRef(null);
        const tooltipRef = useRef(null);

        useEffect(() => {
          if (!chartRef.current || !data || !fullSprintData) return;
          if (chartInstance.current) chartInstance.current.destroy();

          if (!tooltipRef.current) {
            tooltipRef.current = document.createElement('div');
            tooltipRef.current.className = 'chart-tooltip';
            document.body.appendChild(tooltipRef.current);
          }

          const buildDeveloperTooltip = (developerName, sprintData, metric) => {
            const devData = sprintData.sprints.map(sprint => {
              const dev = sprint.developer_summary.find(d => d.name === developerName);
              if (!dev) return null;
              return {
                sprintName: sprint.sprint.name.replace('DevicesTITAN_', ''),
                jira: dev.sprint_jira,
                git: dev.sprint_git,
                total: dev.sprint_total
              };
            }).filter(Boolean);
            
            const total = devData.reduce((sum, d) => sum + d[metric], 0);
            let html = `<div class="tooltip-header">${developerName}</div>`;
            devData.forEach(d => {
              const value = metric === 'total' ? d.total : (metric === 'jira' ? d.jira : d.git);
              const extra = metric === 'total' ? ` (J:${d.jira}, R:${d.git})` : '';
              html += `<div class="tooltip-row"><span class="sprint-name">${d.sprintName}:</span><span class="sprint-data">${value}${extra}</span></div>`;
            });
            html += `<div class="tooltip-total">Total: ${total} actions</div>`;
            return html;
          };

          const buildAverageTooltip = (label, value) => {
            return `<div class="tooltip-average">${label}<br/>${value.toFixed(1)} actions</div>`;
          };

          const ctx = chartRef.current.getContext("2d");
          chartInstance.current = new Chart(ctx, {
            type: "line",
            data: { labels: data.labels, datasets: data.datasets },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              interaction: { mode: 'dataset', intersect: false },
              plugins: {
                legend: { display: true, position: 'right', labels: { usePointStyle: true, padding: 12, font: { size: 13, weight: '500' } } },
                title: { display: true, text: title, font: { size: 20, weight: 'bold' }, color: '#1f2937', padding: { top: 10, bottom: 15 } },
                tooltip: {
                  enabled: false,
                  external: (context) => {
                    const tooltipEl = tooltipRef.current;
                    const tooltipModel = context.tooltip;
                    if (tooltipModel.opacity === 0) { tooltipEl.style.display = 'none'; return; }
                    if (tooltipModel.dataPoints && tooltipModel.dataPoints.length > 0) {
                      const datasetIndex = tooltipModel.dataPoints[0].datasetIndex;
                      const dataset = data.datasets[datasetIndex];
                      if (dataset.isAverage) {
                        tooltipEl.innerHTML = buildAverageTooltip(dataset.label, tooltipModel.dataPoints[0].parsed.y);
                      } else {
                        tooltipEl.innerHTML = buildDeveloperTooltip(dataset.label, fullSprintData, metricType);
                      }
                      const position = context.chart.canvas.getBoundingClientRect();
                      tooltipEl.style.display = 'block';
                      tooltipEl.style.left = position.left + window.pageXOffset + tooltipModel.caretX + 'px';
                      tooltipEl.style.top = position.top + window.pageYOffset + tooltipModel.caretY + 'px';
                    }
                  }
                }
              },
              scales: {
                x: { title: { display: true, text: 'Sprint', font: { size: 14, weight: 'bold' } }, ticks: { maxRotation: 45, minRotation: 45, font: { size: 12 } }, grid: { color: '#e5e7eb' } },
                y: { beginAtZero: true, title: { display: true, text: 'Actions', font: { size: 14, weight: 'bold' } }, ticks: { color: '#6b7280', font: { size: 12 } }, grid: { color: '#e5e7eb' } }
              },
              onHover: (event, activeElements, chart) => {
                if (activeElements.length > 0) {
                  const datasetIndex = activeElements[0].datasetIndex;
                  chart.data.datasets.forEach((dataset, idx) => {
                    if (idx === datasetIndex) {
                      dataset.borderWidth = 3; dataset.pointRadius = 4; dataset.borderDash = [];
                    } else {
                      dataset.borderWidth = 1.5; dataset.pointRadius = 2; dataset.borderDash = dataset.defaultBorderDash || [];
                    }
                  });
                  chart.update('none');
                } else {
                  chart.data.datasets.forEach(dataset => {
                    dataset.borderWidth = 1.5; dataset.pointRadius = 2; dataset.borderDash = dataset.defaultBorderDash || [];
                  });
                  chart.update('none');
                }
              }
            },
          });

          return () => {
            if (chartInstance.current) chartInstance.current.destroy();
            if (tooltipRef.current) tooltipRef.current.style.display = 'none';
          };
        }, [data, title, metricType, fullSprintData]);

        return <canvas ref={chartRef} className="w-full" style={{ height: '450px' }}></canvas>;
      };

      // ═══════════════════════════════════════════════════════════════════════
      // SIDEBAR NAVIGATION
      // ═══════════════════════════════════════════════════════════════════════

      const Sidebar = ({ currentView, onNavigate, isOpen, toggle }) => {
        return (
          <div className={`sidebar ${isOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
            <div className="sidebar-header">
              <div className="sidebar-title">
                {isOpen ? 'SDM Reports' : 'SDM'}
              </div>
              <button onClick={toggle} className="toggle-btn">
                {isOpen ? '←' : '→'}
              </button>
            </div>
            
            <nav>
              <div 
                className={`nav-item ${currentView === 'daily' ? 'active' : ''}`}
                onClick={() => onNavigate('daily')}
              >
                <span className="nav-item-icon">📅</span>
                {isOpen && <span className="nav-item-text">Daily Activity</span>}
              </div>
              <div 
                className={`nav-item ${currentView === 'sprint' ? 'active' : ''}`}
                onClick={() => onNavigate('sprint')}
              >
                <span className="nav-item-icon">📊</span>
                {isOpen && <span className="nav-item-text">Sprint Activity</span>}
              </div>
            </nav>
            
            {isOpen && (
              <div className="sidebar-footer">
                SDM Tools<br/>Bundled Reports
              </div>
            )}
          </div>
        );
      };

      // ═══════════════════════════════════════════════════════════════════════
      // DAILY ACTIVITY DASHBOARD
      // ═══════════════════════════════════════════════════════════════════════

      const ActivityHeatmap = ({ developers, bucketDisplayNames }) => {
        const getIntensityColor = (total) => {
          if (total === 0) return "bg-gray-100 text-gray-400";
          if (total >= 10) return "bg-green-600 text-white";
          if (total >= 5) return "bg-green-400 text-gray-900";
          if (total >= 3) return "bg-yellow-300 text-gray-900";
          return "bg-blue-200 text-gray-900";
        };

        const getOffHoursColor = (total) => {
          if (total === 0) return "bg-gray-100 text-gray-400";
          if (total >= 5) return "bg-orange-500 text-white";
          if (total >= 3) return "bg-orange-300 text-gray-900";
          return "bg-yellow-200 text-gray-900";
        };

        const buckets = ["8am-10am", "10am-12pm", "12pm-2pm", "2pm-4pm", "4pm-6pm"];

        return (
          <div className="overflow-x-auto">
            <table className="min-w-full bg-white border border-gray-200 text-sm">
              <thead className="bg-telus-purple text-white">
                <tr>
                  <th className="px-4 py-3 text-left">Developer</th>
                  {buckets.map((bucket) => (
                    <th key={bucket} className="px-4 py-3 text-center">{bucketDisplayNames[bucket] || bucket}</th>
                  ))}
                  <th className="px-4 py-3 text-center bg-orange-600">Off-Hours</th>
                  <th className="px-4 py-3 text-center bg-telus-green">Total</th>
                </tr>
              </thead>
              <tbody>
                {developers.filter((d) => d.daily_total.total > 0).slice(0, 15).map((dev, idx) => (
                  <tr key={idx} className="border-t hover:bg-gray-50">
                    <td className="px-4 py-2 font-medium">{dev.name}</td>
                    {buckets.map((bucket) => (
                      <td key={bucket} className={`px-4 py-2 text-center ${getIntensityColor(dev.buckets[bucket]?.total || 0)}`}>
                        <div className="font-bold">{dev.buckets[bucket]?.total || "-"}</div>
                        {dev.buckets[bucket]?.total > 0 && (<div className="text-xs">J:{dev.buckets[bucket].jira} R:{dev.buckets[bucket].git}</div>)}
                      </td>
                    ))}
                    <td className={`px-4 py-2 text-center ${getOffHoursColor(dev.off_hours.total)}`}>
                      <div className="font-bold">{dev.off_hours.total || "-"}</div>
                      {dev.off_hours.total > 0 && (<div className="text-xs">J:{dev.off_hours.jira} R:{dev.off_hours.git}</div>)}
                    </td>
                    <td className="px-4 py-2 text-center bg-green-100 font-bold">{dev.daily_total.total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="mt-4 text-xs text-gray-600 flex gap-4">
              <span className="flex items-center gap-2"><span className="w-4 h-4 bg-green-600"></span> 10+</span>
              <span className="flex items-center gap-2"><span className="w-4 h-4 bg-green-400"></span> 5-9</span>
              <span className="flex items-center gap-2"><span className="w-4 h-4 bg-yellow-300"></span> 3-4</span>
              <span className="flex items-center gap-2"><span className="w-4 h-4 bg-blue-200"></span> 1-2</span>
            </div>
          </div>
        );
      };

      const DailyActivityDashboard = ({ data }) => {
        const bucketDisplayNames = {
          "8am-10am": "10am", "10am-12pm": "12pm", "12pm-2pm": "2pm", "2pm-4pm": "4pm", "4pm-6pm": "6pm",
        };

        const bucketActivityData = {
          labels: data.metadata.time_buckets.map((b) => bucketDisplayNames[b] || b).concat(["Off-Hours"]),
          datasets: [
            {
              label: "Jira Actions",
              data: [...data.metadata.time_buckets.map((bucket) => data.developers.reduce((sum, dev) => sum + (dev.buckets[bucket]?.jira || 0), 0)),
                data.developers.reduce((sum, dev) => sum + dev.off_hours.jira, 0)],
              backgroundColor: "#4B0082", borderColor: "#4B0082", borderWidth: 1,
            },
            {
              label: "Repo Actions",
              data: [...data.metadata.time_buckets.map((bucket) => data.developers.reduce((sum, dev) => sum + (dev.buckets[bucket]?.git || 0), 0)),
                data.developers.reduce((sum, dev) => sum + dev.off_hours.git, 0)],
              backgroundColor: "#66CC00", borderColor: "#66CC00", borderWidth: 1,
            },
          ],
        };

        const offHoursData = {
          labels: ["Regular Hours", "Off-Hours"],
          values: [data.summary.total_activity - data.summary.off_hours_activity, data.summary.off_hours_activity],
        };

        const developerComparisonData = {
          labels: data.developers.filter((d) => d.daily_total.total > 0).slice(0, 10).map((d) => d.name.split(" ")[0]),
          datasets: [
            { label: "Jira", data: data.developers.filter((d) => d.daily_total.total > 0).slice(0, 10).map((d) => d.daily_total.jira), backgroundColor: "#4B0082" },
            { label: "Repo", data: data.developers.filter((d) => d.daily_total.total > 0).slice(0, 10).map((d) => d.daily_total.git), backgroundColor: "#66CC00" },
          ],
        };

        return (
          <div className="min-h-screen bg-gray-50">
            <div className="gradient-bg text-white py-12">
              <div className="container mx-auto px-6">
                <h1 className="text-4xl font-bold mb-4">Daily Activity Report</h1>
                <p className="text-xl opacity-90">Report Date: {data.metadata.report_date} • Timezone: {data.metadata.timezone}</p>
              </div>
            </div>

            <div className="container mx-auto px-6 py-8">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
                <div className="card-hover bg-white rounded-xl shadow-lg p-6 border-l-4 border-telus-purple">
                  <div className="text-gray-600 text-sm">Total Developers</div>
                  <div className="text-3xl font-bold text-telus-purple">{data.summary.total_developers}</div>
                </div>
                <div className="card-hover bg-white rounded-xl shadow-lg p-6 border-l-4 border-telus-green">
                  <div className="text-gray-600 text-sm">Total Activity</div>
                  <div className="text-3xl font-bold text-telus-green">{data.summary.total_activity}</div>
                </div>
                <div className="card-hover bg-white rounded-xl shadow-lg p-6 border-l-4 border-telus-blue">
                  <div className="text-gray-600 text-sm">Most Active Bucket</div>
                  <div className="text-xl font-bold text-telus-blue">{bucketDisplayNames[data.summary.most_active_bucket] || data.summary.most_active_bucket}</div>
                </div>
                <div className="card-hover bg-white rounded-xl shadow-lg p-6 border-l-4 border-orange-500">
                  <div className="text-gray-600 text-sm">Off-Hours Activity</div>
                  <div className="text-3xl font-bold text-orange-500">{data.summary.off_hours_percentage}%</div>
                </div>
              </div>

              <div className="card-hover bg-white rounded-xl shadow-lg p-6 mb-12">
                <h2 className="text-2xl font-bold text-telus-purple mb-4">Activity Heatmap</h2>
                <ActivityHeatmap developers={data.developers} bucketDisplayNames={bucketDisplayNames} />
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
                <div className="card-hover bg-white rounded-xl shadow-lg p-6">
                  <BarChart data={bucketActivityData} title="Activity by Time Bucket" />
                </div>
                <div className="card-hover bg-white rounded-xl shadow-lg p-6">
                  <DoughnutChart data={offHoursData} title="Regular vs Off-Hours Activity" />
                </div>
              </div>

              <div className="card-hover bg-white rounded-xl shadow-lg p-6 mb-12">
                <BarChart data={developerComparisonData} title="Ranking - Jira vs Repo Activity" />
              </div>
            </div>
          </div>
        );
      };

      // ═══════════════════════════════════════════════════════════════════════
      // SPRINT ACTIVITY DASHBOARD (PARTIAL - continues in next section)
      // ═══════════════════════════════════════════════════════════════════════

      const SprintActivityTable = ({ tableData }) => {
        if (!tableData) return null;

        const getActivityColor = (total) => {
          if (total === 0) return { className: 'text-gray-400', style: { backgroundColor: 'rgba(249, 250, 251, 0.5)' } };
          if (total >= 50) return { className: 'text-gray-900', style: { backgroundColor: 'rgba(134, 239, 172, 0.6)' } };
          if (total >= 30) return { className: 'text-gray-900', style: { backgroundColor: 'rgba(187, 247, 208, 0.55)' } };
          if (total >= 15) return { className: 'text-gray-900', style: { backgroundColor: 'rgba(254, 249, 195, 0.5)' } };
          if (total >= 5) return { className: 'text-gray-900', style: { backgroundColor: 'rgba(191, 219, 254, 0.6)' } };
          return { className: 'text-gray-700', style: { backgroundColor: 'rgba(219, 234, 254, 0.5)' } };
        };

        return (
          <div className="bg-white rounded-lg shadow-lg overflow-hidden mb-8">
            <div className="px-6 py-4 bg-gradient-to-r from-telus-purple to-telus-light-purple">
              <h3 className="text-xl font-bold text-white">Sprint Activity Heatmap</h3>
              <p className="text-sm text-white opacity-90 mt-1">Activity breakdown by developer and sprint</p>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider sticky left-0 bg-gray-50">Developer</th>
                    {tableData.sprints.map((sprint) => (
                      <th key={sprint.id} className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        <div className="whitespace-normal" style={{ maxWidth: '100px', lineHeight: '1.2' }}>{sprint.name.replace('DevicesTITAN_', '')}</div>
                      </th>
                    ))}
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-100">Total</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {tableData.developers.map((dev) => (
                    <tr key={dev.email} className="hover:bg-gray-50">
                      <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900 sticky left-0 bg-white">{dev.name}</td>
                      {tableData.sprints.map((sprint) => {
                        const sprintData = dev.sprintData[sprint.id] || { total: 0, jira: 0, git: 0 };
                        const colorData = getActivityColor(sprintData.total);
                        return (
                          <td key={sprint.id} className={`px-2 py-2 text-center ${colorData.className}`} style={colorData.style}>
                            <div className="text-sm font-bold">{sprintData.total || '-'}</div>
                            {sprintData.total > 0 && <div className="text-xs opacity-80">J:{sprintData.jira} R:{sprintData.git}</div>}
                          </td>
                        );
                      })}
                      <td className="px-4 py-3 text-center bg-gray-100 font-bold text-gray-900">{dev.total}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="px-6 py-3 bg-gray-50 border-t border-gray-200">
              <div className="flex items-center gap-4 text-xs text-gray-600">
                <span className="font-semibold">Legend:</span>
                <span className="flex items-center gap-1"><span className="w-4 h-4 inline-block" style={{backgroundColor: 'rgba(134, 239, 172, 0.6)'}}></span> 50+</span>
                <span className="flex items-center gap-1"><span className="w-4 h-4 inline-block" style={{backgroundColor: 'rgba(187, 247, 208, 0.55)'}}></span> 30-49</span>
                <span className="flex items-center gap-1"><span className="w-4 h-4 inline-block" style={{backgroundColor: 'rgba(254, 249, 195, 0.5)'}}></span> 15-29</span>
                <span className="flex items-center gap-1"><span className="w-4 h-4 inline-block" style={{backgroundColor: 'rgba(191, 219, 254, 0.6)'}}></span> 5-14</span>
                <span className="flex items-center gap-1"><span className="w-4 h-4 inline-block" style={{backgroundColor: 'rgba(219, 234, 254, 0.5)'}}></span> 1-4</span>
              </div>
            </div>
          </div>
        );
      };

      const SprintActivityDashboard = ({ data }) => {
        const [chartData, setChartData] = useState(null);
        const [tableData, setTableData] = useState(null);

        const prepareLineChartData = (report, metricType) => {
          const reversedSprints = [...report.sprints].reverse();
          const sprintLabels = reversedSprints.map(s => s.sprint.name.replace('DevicesTITAN_', ''));
          const developerEmails = [...new Set(reversedSprints.flatMap(s => s.developer_summary.map(d => d.email)))];
          
          const datasets = developerEmails.map((email, idx) => {
            const devName = reversedSprints.flatMap(s => s.developer_summary).find(d => d.email === email)?.name || email;
            const data = reversedSprints.map(sprint => {
              const dev = sprint.developer_summary.find(d => d.email === email);
              if (!dev) return 0;
              switch(metricType) {
                case 'jira': return dev.sprint_jira;
                case 'git': return dev.sprint_git;
                case 'total': return dev.sprint_total;
                default: return 0;
              }
            });
            
            return {
              label: devName, data: data,
              borderColor: DEVELOPER_COLORS[idx % DEVELOPER_COLORS.length],
              backgroundColor: DEVELOPER_COLORS[idx % DEVELOPER_COLORS.length],
              borderWidth: 1.5, tension: 0, borderDash: [5, 5], defaultBorderDash: [5, 5],
              pointRadius: 2, pointHoverRadius: 4,
              pointBackgroundColor: DEVELOPER_COLORS[idx % DEVELOPER_COLORS.length],
              isAverage: false
            };
          });
          
          const sprintAverages = reversedSprints.map(sprint => {
            const values = sprint.developer_summary.map(dev => {
              switch(metricType) {
                case 'jira': return dev.sprint_jira;
                case 'git': return dev.sprint_git;
                case 'total': return dev.sprint_total;
                default: return 0;
              }
            });
            return values.reduce((sum, v) => sum + v, 0) / values.length;
          });
          
          const allValues = reversedSprints.flatMap(sprint => sprint.developer_summary.map(dev => {
            switch(metricType) {
              case 'jira': return dev.sprint_jira;
              case 'git': return dev.sprint_git;
              case 'total': return dev.sprint_total;
              default: return 0;
            }
          }));
          const overallAverage = allValues.reduce((sum, v) => sum + v, 0) / allValues.length;
          const overallAverages = new Array(reversedSprints.length).fill(overallAverage);
          
          datasets.push({
            label: 'Sprint Average', data: sprintAverages,
            borderColor: SPRINT_AVG_COLOR, backgroundColor: SPRINT_AVG_COLOR,
            borderWidth: 1.5, tension: 0, borderDash: [10, 5], defaultBorderDash: [10, 5],
            pointRadius: 2, pointHoverRadius: 4, pointBackgroundColor: SPRINT_AVG_COLOR,
            isAverage: true
          });
          
          datasets.push({
            label: 'Overall Average', data: overallAverages,
            borderColor: OVERALL_AVG_COLOR, backgroundColor: OVERALL_AVG_COLOR,
            borderWidth: 1.5, tension: 0, borderDash: [3, 3], defaultBorderDash: [3, 3],
            pointRadius: 0, pointHoverRadius: 2, pointBackgroundColor: OVERALL_AVG_COLOR,
            isAverage: true
          });
          
          return { labels: sprintLabels, datasets: datasets };
        };

        const prepareSprintTableData = (report) => {
          const developerMap = {};
          report.sprints.forEach(sprint => {
            sprint.developer_summary.forEach(dev => {
              if (!developerMap[dev.email]) {
                developerMap[dev.email] = { name: dev.name, email: dev.email, sprintData: {}, total: 0, totalJira: 0, totalGit: 0 };
              }
              developerMap[dev.email].sprintData[sprint.sprint.id] = { total: dev.sprint_total, jira: dev.sprint_jira, git: dev.sprint_git };
              developerMap[dev.email].total += dev.sprint_total;
              developerMap[dev.email].totalJira += dev.sprint_jira;
              developerMap[dev.email].totalGit += dev.sprint_git;
            });
          });
          
          return {
            developers: Object.values(developerMap).sort((a, b) => b.total - a.total),
            sprints: report.sprints.map(s => ({ id: s.sprint.id, name: s.sprint.name })).reverse()
          };
        };

        useEffect(() => {
          const jiraData = prepareLineChartData(data, 'jira');
          const gitData = prepareLineChartData(data, 'git');
          const totalData = prepareLineChartData(data, 'total');
          setChartData({ jiraData, gitData, totalData });
          
          const sprintTable = prepareSprintTableData(data);
          setTableData(sprintTable);
        }, [data]);

        if (!chartData || !tableData) {
          return <div className="min-h-screen flex items-center justify-center"><div className="text-xl text-telus-purple">Loading...</div></div>;
        }

        return (
          <div className="min-h-screen p-6">
            <div className="gradient-bg rounded-lg shadow-lg p-8 mb-8">
              <h1 className="text-4xl font-bold text-white mb-2">Sprint Activity Dashboard</h1>
              <p className="text-white text-lg">Last {data.metadata.sprint_count} Sprint{data.metadata.sprint_count !== 1 ? 's' : ''} ({data.metadata.earliest_sprint.start_date} to {data.metadata.latest_sprint.start_date})</p>
              <p className="text-white text-sm mt-1 opacity-90">Generated: {new Date(data.generated_at).toLocaleString()}</p>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-8">
              <div className="bg-white rounded-lg shadow-lg p-6">
                <LineChart data={chartData.jiraData} title="Jira Actions by Sprint" metricType="jira" fullSprintData={data} />
              </div>
              <div className="bg-white rounded-lg shadow-lg p-6">
                <LineChart data={chartData.gitData} title="Repo Actions by Sprint" metricType="git" fullSprintData={data} />
              </div>
              <div className="bg-white rounded-lg shadow-lg p-6 xl:col-span-2">
                <LineChart data={chartData.totalData} title="Total Actions by Sprint" metricType="total" fullSprintData={data} />
              </div>
            </div>

            <SprintActivityTable tableData={tableData} />

            <div className="text-center text-gray-500 text-sm py-4">
              <p>SDM Tools - Sprint Activity Dashboard</p>
              <p className="text-xs mt-1">Data updated: {new Date(data.generated_at).toLocaleDateString()}</p>
            </div>
          </div>
        );
      };

      // ═══════════════════════════════════════════════════════════════════════
      // MAIN APP WITH NAVIGATION
      // ═══════════════════════════════════════════════════════════════════════

      const BundledReportsApp = () => {
        const [currentView, setCurrentView] = useState('sprint');
        const [sidebarOpen, setSidebarOpen] = useState(true);

        return (
          <>
            <Sidebar 
              currentView={currentView} 
              onNavigate={setCurrentView}
              isOpen={sidebarOpen}
              toggle={() => setSidebarOpen(!sidebarOpen)} 
            />
            <div className={`main-content ${sidebarOpen ? 'with-sidebar-open' : 'with-sidebar-closed'}`}>
              {currentView === 'daily' && <DailyActivityDashboard data={EMBEDDED_DATA.daily} />}
              {currentView === 'sprint' && <SprintActivityDashboard data={EMBEDDED_DATA.sprint} />}
            </div>
          </>
        );
      };

      // Render the app
      const root = ReactDOM.createRoot(document.getElementById('root'));
      root.render(<BundledReportsApp />);
"""

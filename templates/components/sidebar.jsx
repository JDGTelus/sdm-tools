// Sidebar Navigation Component
const Sidebar = ({ currentView, onNavigate, isOpen, toggle, reports }) => {
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
        {reports.map(report => (
          <div
            key={report.view_name}
            className={`nav-item ${currentView === report.view_name ? 'active' : ''}`}
            onClick={() => onNavigate(report.view_name)}
          >
            <span className="nav-item-icon">{report.icon}</span>
            {isOpen && <span className="nav-item-text">{report.title}</span>}
          </div>
        ))}
      </nav>

      {isOpen && (
        <div className="sidebar-footer">
          SDM Tools<br/>Bundled Reports
        </div>
      )}
    </div>
  );
};

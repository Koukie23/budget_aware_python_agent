import { CodeOutlined, HistoryOutlined } from "@ant-design/icons";
import { Layout, Menu, Typography } from "antd";
import { Link, Route, Routes, useLocation } from "react-router-dom";
import { History } from "./pages/History";
import { Workbench } from "./pages/Workbench";

const { Header, Content } = Layout;

export function App() {
  const { pathname } = useLocation();
  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Header className="app-header">
        <Typography.Title level={4} style={{ margin: 0, whiteSpace: "nowrap" }}>
          Budget-Aware Python Coding Agent
        </Typography.Title>
        <Menu
          mode="horizontal"
          selectedKeys={[pathname === "/history" ? "history" : "workbench"]}
          style={{ flex: 1, justifyContent: "flex-end", borderBottom: "none", background: "transparent" }}
          items={[
            { key: "workbench", icon: <CodeOutlined />, label: <Link to="/">Coding Workbench</Link> },
            { key: "history", icon: <HistoryOutlined />, label: <Link to="/history">History</Link> },
          ]}
        />
      </Header>
      <Content className="app-content">
        <Routes>
          <Route path="/" element={<Workbench />} />
          <Route path="/history" element={<History />} />
        </Routes>
      </Content>
    </Layout>
  );
}

import type { ThemeConfig } from "antd";

export const colors = {
  background: "#F4F2EF",
  card: "#FCFBF9",
  primary: "#73877B",
  secondary: "#8192A3",
  danger: "#A66F66",
  text: "#303936",
  border: "#DDDCD6",
  warning: "#B39469",
};

export const theme: ThemeConfig = {
  token: {
    colorPrimary: colors.primary,
    colorInfo: colors.secondary,
    colorSuccess: colors.primary,
    colorError: colors.danger,
    colorWarning: colors.warning,
    colorText: colors.text,
    colorBorder: colors.border,
    colorBorderSecondary: colors.border,
    colorBgLayout: colors.background,
    colorBgContainer: colors.card,
    borderRadius: 8,
    boxShadow: "0 1px 3px rgba(48, 57, 54, 0.06)",
    fontFamily:
      "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
  },
  components: {
    Layout: { headerBg: colors.card, bodyBg: colors.background },
    Card: { boxShadowTertiary: "0 1px 3px rgba(48, 57, 54, 0.06)" },
  },
};

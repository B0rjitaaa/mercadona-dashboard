import { createBrowserRouter } from "react-router-dom";
import { Layout } from "./components/Layout";
import { DashboardPage } from "./features/dashboard/DashboardPage";
import { ReceiptsPage } from "./features/receipts/ReceiptsPage";
import { ProductsPage } from "./features/products/ProductsPage";
import { SpendingPage } from "./features/spending/SpendingPage";
import { ReviewPage } from "./features/review/ReviewPage";
import { SettingsPage } from "./features/settings/SettingsPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "receipts", element: <ReceiptsPage /> },
      { path: "products", element: <ProductsPage /> },
      { path: "spending", element: <SpendingPage /> },
      { path: "review", element: <ReviewPage /> },
      { path: "settings", element: <SettingsPage /> },
    ],
  },
]);

import { createBrowserRouter } from "react-router-dom";
import { Layout } from "./components/Layout";
import { DashboardPage } from "./features/dashboard/DashboardPage";
import { ProductDetailPage } from "./features/products/ProductDetailPage";
import { PricesPage } from "./features/prices/PricesPage";
import { ProductsPage } from "./features/products/ProductsPage";
import { ReceiptDetailPage } from "./features/receipts/ReceiptDetailPage";
import { ReceiptsPage } from "./features/receipts/ReceiptsPage";
import { ReviewPage } from "./features/review/ReviewPage";
import { SettingsPage } from "./features/settings/SettingsPage";
import { SpendingPage } from "./features/spending/SpendingPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "spending", element: <SpendingPage /> },
      { path: "receipts", element: <ReceiptsPage /> },
      { path: "receipts/:id", element: <ReceiptDetailPage /> },
      { path: "products", element: <ProductsPage /> },
      { path: "products/:id", element: <ProductDetailPage /> },
      { path: "products/unidentified/:description", element: <ProductDetailPage /> },
      { path: "prices", element: <PricesPage /> },
      { path: "review", element: <ReviewPage /> },
      { path: "settings", element: <SettingsPage /> },
    ],
  },
]);

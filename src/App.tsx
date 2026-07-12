import { createBrowserRouter, RouterProvider, Outlet, useNavigation } from 'react-router-dom';
import { fetchAssets, fetchAssetDetail, fetchCalibration } from './api';
import Sidebar from './components/Sidebar';
import AssetList from './components/AssetList';
import AssetDetail from './components/AssetDetail';
import Calibration from './components/Calibration';

/* ── Layout ────────────────────────────────────────────────────────── */

function Layout() {
  const navigation = useNavigation();

  return (
    <div className="flex h-dvh w-dvw overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-6 lg:p-8">
        {/* Inline loading indicator — subtle thin bar at top */}
        {navigation.state === 'loading' && (
          <div className="absolute top-0 left-0 right-0 h-0.5 z-50">
            <div className="h-full bg-teal animate-pulse rounded-full" style={{ width: '30%' }} />
          </div>
        )}
        <Outlet />
      </main>
    </div>
  );
}

/* ── Loaders ────────────────────────────────────────────────────────── */

async function assetsLoader() {
  return fetchAssets();
}

async function assetDetailLoader({ params }: { params: { assetId: string } }) {
  return fetchAssetDetail(params.assetId);
}

async function calibrationLoader() {
  return fetchCalibration();
}

/* ── Router ─────────────────────────────────────────────────────────── */

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      {
        path: '/',
        element: <AssetList />,
        loader: assetsLoader,
      },
      {
        path: '/asset/:assetId',
        element: <AssetDetail />,
        loader: assetDetailLoader,
      },
      {
        path: '/calibration',
        element: <Calibration />,
        loader: calibrationLoader,
      },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
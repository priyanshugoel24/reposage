const API_URL = process.env.NEXT_PUBLIC_API_URL;

export async function checkHealth(): Promise<unknown> {
  const response = await fetch(`${API_URL}/health`);

  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

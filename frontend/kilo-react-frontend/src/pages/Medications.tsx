import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/shared/Button';
import { Card } from '../components/shared/Card';
import { CameraCapture } from '../components/shared/CameraCapture';
import { Medication } from '../types';
import api from '../services/api';

const Medications: React.FC = () => {
  const navigate = useNavigate();
  const [medications, setMedications] = useState<Medication[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCamera, setShowCamera] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState<{
    success: boolean;
    message: string;
    data?: { ocr_text?: string } | Record<string, unknown>;
  } | null>(null);
  const [editingMed, setEditingMed] = useState<Medication | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editForm, setEditForm] = useState({
    name: '',
    dosage: '',
    schedule: '',
    prescriber: '',
    quantity: 0,
    instructions: '',
    frequency_per_day: 1,
    times: [] as string[] // Array of times like ["08:00", "20:00"]
  });

  useEffect(() => {
    fetchMedications();
  }, []);

  const fetchMedications = async () => {
    try {
      const response = await api.get('/meds');
      setMedications(response.data);
    } catch (error) {
      console.error('Failed to fetch medications:', error);
    } finally {
      setLoading(false);
    }
  };

  const takeMedication = async (id: number) => {
    try {
      await api.post(`/meds/${id}/take`);
      fetchMedications();
    } catch (error) {
      console.error('Failed to mark medication as taken:', error);
    }
  };

  const startEdit = (med: Medication) => {
    setEditingMed(med);
    setEditForm({
      name: med.name || '',
      dosage: med.dosage || '',
      schedule: med.schedule || '',
      prescriber: med.prescriber || '',
      quantity: med.quantity || 0,
      instructions: med.instructions || '',
      frequency_per_day: med.frequency_per_day || 1,
      times: med.times ? med.times.split(',') : []
    });
  };

  const saveEdit = async () => {
    if (!editingMed) return;
    try {
      // Convert times array to comma-separated string
      const medData = {
        ...editForm,
        times: editForm.times.join(',')
      };
      await api.put(`/meds/${editingMed.id}`, medData);
      setEditingMed(null);
      fetchMedications();
    } catch (error) {
      console.error('Failed to update medication:', error);
      alert('Failed to update medication');
    }
  };

  const addMedication = async () => {
    if (!editForm.name.trim()) {
      alert('Medication name is required');
      return;
    }
    try {
      // Convert times array to comma-separated string
      const medData = {
        ...editForm,
        times: editForm.times.join(',')
      };
      await api.post('/meds/add', medData);
      setShowAddForm(false);
      setEditForm({
        name: '',
        dosage: '',
        schedule: '',
        prescriber: '',
        quantity: 0,
        instructions: '',
        frequency_per_day: 1,
        times: []
      });
      fetchMedications();
    } catch (error) {
      console.error('Failed to add medication:', error);
      alert('Failed to add medication');
    }
  };

  const deleteMedication = async (id: number, name: string) => {
    if (!window.confirm(`Are you sure you want to delete ${name || 'this medication'}?`)) return;
    try {
      await api.delete(`/meds/${id}`);
      fetchMedications();
    } catch (error) {
      console.error('Failed to delete medication:', error);
      alert('Failed to delete medication');
    }
  };

  const handlePrescriptionCapture = async (imageBlob: Blob, imageDataUrl: string, allImages?: Blob[]) => {
    setShowCamera(false);
    setScanning(true);
    setScanResult(null);

    try {
      // Create FormData to send all captured images
      const formData = new FormData();
      if (allImages && allImages.length > 0) {
        // Send all images for stitching
        allImages.forEach((img, idx) => {
          formData.append('files', img, `prescription_${idx}.jpg`);
        });
      } else {
        // Fallback to single image
        formData.append('file', imageBlob, 'prescription.jpg');
      }

      // Send to meds service for OCR extraction (async processing)
      const submitResponse = await api.post('/meds/extract', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const { job_id } = submitResponse.data;
      if (!job_id) {
        throw new Error('No job_id returned from server');
      }

      console.log(`[OCR] Job submitted: ${job_id}, polling for results...`);

      // Poll for OCR results every 3 seconds
      const maxPolls = 60; // Poll for up to 3 minutes
      let pollCount = 0;

      const pollForResults = async (): Promise<void> => {
        while (pollCount < maxPolls) {
          pollCount++;

          try {
            const statusResponse = await api.get(`/meds/extract/${job_id}/status`);
            const { status, result, error, ocr_text } = statusResponse.data;

            console.log(`[OCR] Poll ${pollCount}: status=${status}`);

            if (status === 'completed' && result) {
              // Success! Medication was extracted and added
              setScanResult({
                success: true,
                message: result.name
                  ? `✓ Added ${result.name}!`
                  : '✓ Prescription scanned! Check data below.',
                data: { ...result, ocr_text },
              });
              fetchMedications(); // Refresh medications list
              return;
            } else if (status === 'failed') {
              // OCR processing failed
              setScanResult({
                success: false,
                message: error || 'OCR processing failed. Please try again with better lighting.',
              });
              return;
            } else if (status === 'processing' || status === 'pending') {
              // Still processing, wait and poll again
              await new Promise((resolve) => setTimeout(resolve, 3000)); // Wait 3 seconds
            } else {
              // Unknown status
              throw new Error(`Unknown job status: ${status}`);
            }
          } catch (pollError: unknown) {
            console.error('[OCR] Polling error:', pollError);
            // Continue polling unless we've exceeded max polls
            if (pollCount >= maxPolls) {
              throw pollError;
            }
            await new Promise((resolve) => setTimeout(resolve, 3000));
          }
        }

        // Timeout after max polls
        throw new Error('OCR processing timeout. Please try again.');
      };

      await pollForResults();

    } catch (error: unknown) {
      console.error('Prescription scan error:', error);
      const message = (error && typeof error === 'object' && 'response' in error && (error as any).response?.data?.detail)
        || (error instanceof Error ? error.message : null)
        || 'Failed to scan prescription. Please try again.';
      setScanResult({
        success: false,
        message,
      });
    } finally {
      setScanning(false);
    }
  };

  return (
    <div className="min-h-screen zombie-gradient p-2">
      <div className="flex justify-between items-center mb-2">
        <h1 className="font-header text-xl text-zombie-green neon-text">💊 MEDICATIONS</h1>
        <Button onClick={() => navigate('/dashboard')} variant="secondary" size="sm">
          ← BACK
        </Button>
      </div>

      <div className="mb-2 flex gap-2">
        <Button
          onClick={() => setShowCamera(true)}
          variant="primary"
          size="md"
          className="flex-1"
          disabled={scanning}
        >
          {scanning ? '⏳ SCANNING...' : '📷 SCAN PRESCRIPTION'}
        </Button>
        <Button
          onClick={() => setShowAddForm(!showAddForm)}
          variant="secondary"
          size="md"
          className="flex-1"
        >
          {showAddForm ? '✕ CANCEL' : '➕ ADD MANUALLY'}
        </Button>
      </div>

      {showAddForm && (
        <Card className="mb-2 py-3 px-4">
          <h3 className="text-lg font-bold text-zombie-green terminal-glow mb-3">ADD NEW MEDICATION</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-semibold text-zombie-green mb-1">Medication Name *</label>
              <input
                type="text"
                value={editForm.name}
                onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                className="w-full p-2 bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                placeholder="e.g., Aspirin"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-zombie-green mb-1">Dosage</label>
              <input
                type="text"
                value={editForm.dosage}
                onChange={(e) => setEditForm({ ...editForm, dosage: e.target.value })}
                className="w-full p-2 bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                placeholder="e.g., 500mg"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-zombie-green mb-1">Schedule</label>
              <input
                type="text"
                value={editForm.schedule}
                onChange={(e) => setEditForm({ ...editForm, schedule: e.target.value })}
                className="w-full p-2 bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                placeholder="e.g., Twice daily"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-zombie-green mb-1">Prescriber</label>
              <input
                type="text"
                value={editForm.prescriber}
                onChange={(e) => setEditForm({ ...editForm, prescriber: e.target.value })}
                className="w-full p-2 bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                placeholder="e.g., Dr. Smith"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-zombie-green mb-1">Quantity</label>
              <input
                type="number"
                value={editForm.quantity}
                onChange={(e) => setEditForm({ ...editForm, quantity: parseInt(e.target.value) || 0 })}
                className="w-full p-2 bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                placeholder="e.g., 30"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-zombie-green mb-1">Instructions</label>
              <textarea
                value={editForm.instructions}
                onChange={(e) => setEditForm({ ...editForm, instructions: e.target.value })}
                className="w-full p-2 bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                placeholder="e.g., Take with food"
                rows={2}
              />
            </div>

            {/* Reminder Schedule */}
            <div className="border-t-2 border-zombie-green pt-3 mt-3">
              <h4 className="text-sm font-bold text-zombie-green mb-2">⏰ REMINDER SCHEDULE</h4>
              
              <div className="mb-3">
                <label className="block text-sm font-semibold text-zombie-green mb-1">
                  How many times per day? *
                </label>
                <select
                  value={editForm.frequency_per_day}
                  onChange={(e) => {
                    const freq = parseInt(e.target.value);
                    setEditForm({ 
                      ...editForm, 
                      frequency_per_day: freq,
                      times: Array(freq).fill('09:00') // Initialize with default times
                    });
                  }}
                  className="w-full p-2 bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                >
                  <option value={1}>Once daily</option>
                  <option value={2}>Twice daily</option>
                  <option value={3}>Three times daily</option>
                  <option value={4}>Four times daily</option>
                  <option value={6}>Six times daily</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="block text-sm font-semibold text-zombie-green mb-1">
                  Set specific times:
                </label>
                {Array.from({ length: editForm.frequency_per_day }).map((_, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <span className="text-zombie-green text-sm w-16">Time {idx + 1}:</span>
                    <input
                      type="time"
                      value={editForm.times[idx] || '09:00'}
                      onChange={(e) => {
                        const newTimes = [...editForm.times];
                        newTimes[idx] = e.target.value;
                        setEditForm({ ...editForm, times: newTimes });
                      }}
                      className="flex-1 p-2 bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                    />
                  </div>
                ))}
                <p className="text-xs text-zombie-green/70 mt-2">
                  💡 Reminders will be automatically created for these times
                </p>
              </div>
            </div>

            <Button
              onClick={addMedication}
              variant="success"
              size="md"
              className="w-full"
            >
              ✓ ADD MEDICATION & CREATE REMINDERS
            </Button>
          </div>
        </Card>
      )}

      {scanResult && (
        <Card className="mb-2 py-2 px-3">
          <div className={scanResult.success ? 'text-zombie-green' : 'text-yellow-600'}>
            <p className="text-lg font-semibold mb-2">{scanResult.message}</p>
            {scanResult.data && ('ocr_text' in scanResult.data) && (
              <details className="mt-2">
                <summary className="cursor-pointer text-sm underline">View OCR Text</summary>
                <pre className="text-xs mt-2 p-2 bg-dark-card rounded overflow-auto max-h-40">
                  {(scanResult.data as { ocr_text?: string }).ocr_text}
                </pre>
              </details>
            )}
          </div>
          <Button
            onClick={() => setScanResult(null)}
            variant="secondary"
            size="sm"
            className="mt-4"
          >
            DISMISS
          </Button>
        </Card>
      )}

      {showCamera && (
        <CameraCapture
          type="prescription"
          onCapture={handlePrescriptionCapture}
          onClose={() => setShowCamera(false)}
        />
      )}

      <div className="space-y-2">
        <h2 className="text-base font-semibold text-zombie-green terminal-glow">TODAY'S MEDICATIONS:</h2>
        {loading ? (
          <div className="text-center py-4 text-zombie-green">Loading medications...</div>
        ) : medications.length === 0 ? (
          <Card>
            <p className="text-center text-zombie-green">No medications scheduled</p>
          </Card>
        ) : (
          medications.map((med) => (
            <Card key={med.id} className="py-2 px-3">
              <div className="flex justify-between items-start gap-3">
                <div className="flex-1 min-w-0">
                  <h3 className="font-header text-xl text-zombie-green neon-text mb-1">{med.name || '(No name)'}</h3>
                  <div className="text-sm text-zombie-green space-y-0.5">
                    <p>💊 Dosage: <span className="font-semibold">{med.dosage || 'N/A'}</span></p>
                    <p>⏰ Schedule: <span className="font-semibold">{med.schedule || 'N/A'}</span></p>
                    <p>👨‍⚕️ Prescriber: <span className="font-semibold">{med.prescriber || 'N/A'}</span></p>
                    {med.instructions && (
                      <p className="mt-1">📝 {med.instructions}</p>
                    )}
                    {med.nextDose && (
                      <p className="text-terminal-green mt-1 font-semibold terminal-glow">
                        Next dose: {new Date(med.nextDose).toLocaleTimeString()}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex flex-col gap-2">
                  <Button
                    onClick={() => startEdit(med)}
                    variant="primary"
                    size="sm"
                  >
                    ✏️ EDIT
                  </Button>
                  <Button
                    onClick={() => deleteMedication(med.id, med.name)}
                    variant="secondary"
                    size="sm"
                  >
                    🗑️ DELETE
                  </Button>
                  <Button
                    onClick={() => takeMedication(med.id)}
                    variant={med.taken ? 'secondary' : 'success'}
                    size="lg"
                    disabled={med.taken}
                  >
                    {med.taken ? '✓ TAKEN' : 'TAKE NOW'}
                  </Button>
                </div>
              </div>
            </Card>
          ))
        )}
      </div>

      {/* Edit Modal */}
      {editingMed && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center p-4 z-50">
          <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <h2 className="text-2xl font-bold text-zombie-green terminal-glow mb-4">
              EDIT MEDICATION
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-zombie-green font-semibold mb-2">Name:</label>
                <input
                  type="text"
                  value={editForm.name}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                  className="w-full p-3 bg-dark-bg border-2 border-zombie-green/60 text-zombie-green rounded focus:border-zombie-green focus:outline-none"
                  placeholder="e.g., LISINOPRIL"
                />
              </div>
              <div>
                <label className="block text-zombie-green font-semibold mb-2">Dosage:</label>
                <input
                  type="text"
                  value={editForm.dosage}
                  onChange={(e) => setEditForm({ ...editForm, dosage: e.target.value })}
                  className="w-full p-3 bg-dark-bg border-2 border-zombie-green/60 text-zombie-green rounded focus:border-zombie-green focus:outline-none"
                  placeholder="e.g., 10mg"
                />
              </div>
              <div>
                <label className="block text-zombie-green font-semibold mb-2">Schedule:</label>
                <input
                  type="text"
                  value={editForm.schedule}
                  onChange={(e) => setEditForm({ ...editForm, schedule: e.target.value })}
                  className="w-full p-3 bg-dark-bg border-2 border-zombie-green/60 text-zombie-green rounded focus:border-zombie-green focus:outline-none"
                  placeholder="e.g., Once daily"
                />
              </div>
              <div>
                <label className="block text-zombie-green font-semibold mb-2">Prescriber:</label>
                <input
                  type="text"
                  value={editForm.prescriber}
                  onChange={(e) => setEditForm({ ...editForm, prescriber: e.target.value })}
                  className="w-full p-3 bg-dark-bg border-2 border-zombie-green/60 text-zombie-green rounded focus:border-zombie-green focus:outline-none"
                  placeholder="e.g., Dr. Smith"
                />
              </div>
              <div>
                <label className="block text-zombie-green font-semibold mb-2">Quantity:</label>
                <input
                  type="number"
                  value={editForm.quantity}
                  onChange={(e) => setEditForm({ ...editForm, quantity: parseInt(e.target.value) || 0 })}
                  className="w-full p-3 bg-dark-bg border-2 border-zombie-green/60 text-zombie-green rounded focus:border-zombie-green focus:outline-none"
                  placeholder="e.g., 30"
                />
              </div>
              <div>
                <label className="block text-zombie-green font-semibold mb-2">Instructions:</label>
                <textarea
                  value={editForm.instructions}
                  onChange={(e) => setEditForm({ ...editForm, instructions: e.target.value })}
                  className="w-full p-3 bg-dark-bg border-2 border-zombie-green/60 text-zombie-green rounded focus:border-zombie-green focus:outline-none"
                  placeholder="e.g., Take with water"
                  rows={3}
                />
              </div>
              <div className="flex gap-3 mt-6">
                <Button onClick={saveEdit} variant="success" size="lg" className="flex-1">
                  💾 SAVE
                </Button>
                <Button onClick={() => setEditingMed(null)} variant="secondary" size="lg" className="flex-1">
                  CANCEL
                </Button>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};

export default Medications;

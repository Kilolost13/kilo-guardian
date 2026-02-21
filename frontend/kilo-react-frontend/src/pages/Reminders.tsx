import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/shared/Button';
import { Card } from '../components/shared/Card';
import api from '../services/api';

interface Reminder {
  id: number;
  title: string;
  description?: string;
  reminder_time: string;
  recurring: boolean;
  created_at?: string | null;
}

const Reminders: React.FC = () => {
  const navigate = useNavigate();
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddReminder, setShowAddReminder] = useState(false);
  const [showPresets, setShowPresets] = useState(false);
  const [reminderForm, setReminderForm] = useState({
    text: '',
    when: '',
    recurrence: 'once' as 'once' | 'daily' | 'weekly' | 'hourly' | 'twice_weekly_mon_thu' | 'twice_weekly_tue_fri' | 'custom',
    customCron: ''
  });

  // Quick preset templates
  const presets = [
    { name: 'Clean Cat Box', recurrence: 'twice_weekly_mon_thu', icon: '🐱' },
    { name: 'Drink Water', recurrence: 'hourly', icon: '💧' },
    { name: 'Take Medications', recurrence: 'daily', icon: '💊' },
    { name: 'Clean Room', recurrence: 'weekly', icon: '🧹' },
    { name: 'Do Laundry', recurrence: 'weekly', icon: '👕' },
    { name: 'Cook for Myself', recurrence: 'daily', icon: '🍳' },
    { name: 'Check Pet Food', recurrence: 'daily', icon: '🐾' },
    { name: 'Brush Teeth', recurrence: 'daily', icon: '🦷' },
    { name: 'Exercise', recurrence: 'daily', icon: '💪' },
    { name: 'Take Shower', recurrence: 'daily', icon: '🚿' },
  ];

  useEffect(() => {
    fetchReminders();
  }, []);

  const fetchReminders = async () => {
    try {
      setLoading(true);
      const response = await api.get('/reminder/reminders');
      setReminders(response.data.reminders || []);
    } catch (error) {
      console.error('Failed to fetch reminders:', error);
      setReminders([]);
    } finally {
      setLoading(false);
    }
  };

  const handleAddReminder = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // Backend expects title, description, reminder_time, recurring
      await api.post('/reminder/reminders', {
        title: reminderForm.text,
        description: '',
        reminder_time: reminderForm.when,
        recurring: reminderForm.recurrence !== 'once'
      });
      setShowAddReminder(false);
      setReminderForm({ text: '', when: '', recurrence: 'once', customCron: '' });
      fetchReminders();
    } catch (error) {
      console.error('Failed to add reminder:', error);
    }
  };

  const handleDeleteReminder = async (id: number) => {
    try {
      await api.delete(`/reminder/reminders/${id}`);
      fetchReminders();
    } catch (error) {
      console.error('Failed to delete reminder:', error);
    }
  };

  const handlePresetClick = (preset: typeof presets[0]) => {
    // Set default time to tomorrow at 9am
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(9, 0, 0, 0);
    const tomorrowISO = tomorrow.toISOString().slice(0, 16);

    setReminderForm({
      text: preset.name,
      when: tomorrowISO,
      recurrence: preset.recurrence as any,
      customCron: ''
    });
    setShowPresets(false);
    setShowAddReminder(true);
  };

  return (
    <div className="min-h-screen zombie-gradient p-2">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              onClick={() => navigate('/dashboard')}
              size="sm"
            >
              ← BACK
            </Button>
            <h1 className="font-header text-xl text-zombie-green neon-text">🔔 REMINDERS</h1>
          </div>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              onClick={() => {
                setShowPresets(!showPresets);
                setShowAddReminder(false);
              }}
            >
              {showPresets ? 'Hide Presets' : '⚡ Quick Presets'}
            </Button>
            <Button
              variant="primary"
              onClick={() => {
                setShowAddReminder(!showAddReminder);
                setShowPresets(false);
              }}
            >
              {showAddReminder ? 'Cancel' : '+ Custom Reminder'}
            </Button>
          </div>
        </div>

        {/* Quick Presets */}
        {showPresets && (
          <Card className="mb-2 py-3 px-4">
            <h2 className="text-lg font-bold text-zombie-green terminal-glow mb-3">⚡ QUICK PRESET REMINDERS</h2>
            <p className="text-sm text-zombie-green/70 mb-3">Click a preset to quickly create a reminder with pre-configured settings</p>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
              {presets.map((preset) => (
                <button
                  key={preset.name}
                  onClick={() => handlePresetClick(preset)}
                  className="p-3 bg-zombie-dark border-2 border-zombie-green rounded hover:bg-zombie-green hover:text-zombie-dark transition-all text-center"
                >
                  <div className="text-2xl mb-1">{preset.icon}</div>
                  <div className="text-xs font-semibold text-zombie-green">{preset.name}</div>
                  <div className="text-xs text-zombie-green/70 mt-1">
                    {preset.recurrence === 'hourly' && 'Hourly'}
                    {preset.recurrence === 'daily' && 'Daily'}
                    {preset.recurrence === 'weekly' && 'Weekly'}
                    {preset.recurrence === 'twice_weekly_mon_thu' && '2x/week'}
                  </div>
                </button>
              ))}
            </div>
          </Card>
        )}

        {/* Add Reminder Form */}
        {showAddReminder && (
          <Card className="mb-2 py-3 px-4">
            <form onSubmit={handleAddReminder} className="space-y-3">
              <h2 className="text-lg font-bold text-zombie-green terminal-glow mb-3">CREATE NEW REMINDER</h2>

              <div>
                <label className="block text-sm font-semibold text-zombie-green mb-1">
                  Reminder Text *
                </label>
                <input
                  type="text"
                  required
                  value={reminderForm.text}
                  onChange={(e) => setReminderForm({ ...reminderForm, text: e.target.value })}
                  className="w-full p-2 bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                  placeholder="e.g., Clean cat box, Drink water, Take medications"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-zombie-green mb-1">
                  First Reminder Time *
                </label>
                <input
                  type="datetime-local"
                  required
                  value={reminderForm.when}
                  onChange={(e) => setReminderForm({ ...reminderForm, when: e.target.value })}
                  className="w-full p-2 bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-zombie-green mb-1">
                  Recurrence Pattern *
                </label>
                <select
                  value={reminderForm.recurrence}
                  onChange={(e) => setReminderForm({ ...reminderForm, recurrence: e.target.value as any })}
                  className="w-full p-2 bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text"
                >
                  <option value="once">Once (no repeat)</option>
                  <option value="hourly">Hourly</option>
                  <option value="daily">Daily</option>
                  <option value="twice_weekly_mon_thu">Twice Weekly (Mon/Thu)</option>
                  <option value="twice_weekly_tue_fri">Twice Weekly (Tue/Fri)</option>
                  <option value="weekly">Weekly</option>
                  <option value="custom">Custom (cron expression)</option>
                </select>
                <p className="text-xs text-zombie-green/70 mt-1">
                  {reminderForm.recurrence === 'hourly' && '⏱️ Repeats every hour'}
                  {reminderForm.recurrence === 'daily' && '📅 Repeats every day at the same time'}
                  {reminderForm.recurrence === 'twice_weekly_mon_thu' && '📅 Repeats Monday and Thursday'}
                  {reminderForm.recurrence === 'twice_weekly_tue_fri' && '📅 Repeats Tuesday and Friday'}
                  {reminderForm.recurrence === 'weekly' && '📅 Repeats weekly on the same day'}
                  {reminderForm.recurrence === 'once' && '⚡ One-time reminder'}
                  {reminderForm.recurrence === 'custom' && '⚙️ Advanced cron pattern'}
                </p>
              </div>

              {reminderForm.recurrence === 'custom' && (
                <div>
                  <label className="block text-sm font-semibold text-zombie-green mb-1">
                    Cron Expression *
                  </label>
                  <input
                    type="text"
                    required
                    value={reminderForm.customCron}
                    onChange={(e) => setReminderForm({ ...reminderForm, customCron: e.target.value })}
                    className="w-full p-2 bg-zombie-dark text-zombie-green border-2 border-zombie-green rounded terminal-text font-mono"
                    placeholder="e.g., 0 9,15 * * * (9am and 3pm daily)"
                  />
                  <p className="text-xs text-zombie-green/70 mt-1">
                    Format: minute hour day month weekday
                    <br />
                    Example: "0 9 * * 1,4" = 9am on Mondays and Thursdays
                  </p>
                </div>
              )}

              <div className="flex gap-3">
                <button
                  type="submit"
                  className="flex-1 px-6 py-3 bg-green-500 text-white font-semibold rounded-lg hover:bg-zombie-green transition-all min-h-[56px]"
                >
                  Create Reminder
                </button>
                <Button
                  variant="secondary"
                  onClick={() => setShowAddReminder(false)}
                  className="flex-1"
                >
                  Cancel
                </Button>
              </div>
            </form>
          </Card>
        )}

        {/* Reminders List */}
        <div className="mb-2">
          <h2 className="text-base font-semibold text-zombie-green terminal-glow mb-2">ACTIVE REMINDERS:</h2>
        </div>
        {loading ? (
          <div className="text-center py-4 text-zombie-green">Loading reminders...</div>
        ) : reminders.length === 0 ? (
          <Card className="py-3 px-4">
            <p className="text-center text-zombie-green">
              No reminders yet. Click "+ ADD REMINDER" to create one!
            </p>
          </Card>
        ) : (
          <div className="space-y-2">
            {reminders.map((reminder) => (
              <Card key={reminder.id} className="py-2 px-3">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="text-base font-bold text-zombie-green flex-1">
                    {reminder.title}
                  </h3>
                  <button
                    onClick={() => handleDeleteReminder(reminder.id)}
                    className="text-blood-red hover:text-red-700 text-xl font-bold hover:bg-red-500/20 px-2 py-1 rounded"
                    title="Delete reminder"
                  >
                    ×
                  </button>
                </div>

                <div className="space-y-1 text-xs">
                  {reminder.description && (
                    <div className="text-zombie-green/80 mb-1">
                      {reminder.description}
                    </div>
                  )}
                  
                  <div className="flex items-center gap-2 text-zombie-green">
                    <span>⏰</span>
                    <span>{new Date(reminder.reminder_time).toLocaleString()}</span>
                  </div>

                  <div className="flex items-center gap-2 text-zombie-green">
                    <span>{reminder.recurring ? '🔄 Recurring' : '⚡ One-time'}</span>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Reminders;

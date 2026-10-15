document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-meal-form]').forEach((form) => {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const message = form.querySelector('.form-message');
      const mealType = form.dataset.mealType;
      const items = [...form.querySelectorAll('input[name="items"]:checked')].map((input) => input.value);
      const slot = form.querySelector('select[name="slot"]')?.value;
      const button = form.querySelector('button[type="submit"]');
      if (!items.length) { message.textContent = 'Please select at least one food item.'; message.className = 'form-message error-text'; return; }
      if (!slot) { message.textContent = 'Please choose a serving slot.'; message.className = 'form-message error-text'; return; }
      button.disabled = true; button.textContent = 'Saving…';
      try {
        const response = await fetch('/api/selections', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ meal_type: mealType, slot, items }) });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Could not save your selection.');
        message.textContent = data.message; message.className = 'form-message success-text';
        setTimeout(() => window.location.reload(), 650);
      } catch (error) {
        message.textContent = error.message; message.className = 'form-message error-text';
      } finally { button.disabled = false; button.textContent = 'Save selection'; }
    });
  });
  document.querySelectorAll('[data-cancel-meal]').forEach((button) => {
    button.addEventListener('click', async () => {
      if (!window.confirm('Cancel your saved selection for this meal?')) return;
      try {
        const response = await fetch(`/api/selections/${encodeURIComponent(button.dataset.cancelMeal)}`, { method: 'DELETE' });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Could not cancel selection.');
        window.location.reload();
      } catch (error) { window.alert(error.message); }
    });
  });
  document.querySelectorAll('form[data-confirm]').forEach((form) => {
    form.addEventListener('submit', (event) => { if (!window.confirm(form.dataset.confirm)) event.preventDefault(); });
  });
});

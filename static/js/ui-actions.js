/**
 * UI Actions Handler
 * Обрабатывает data-action атрибуты для печати и удаления (CSP-compliant, no inline handlers)
 */

document.addEventListener('DOMContentLoaded', function () {
  // Handle print action
  document.addEventListener('click', function (e) {
    const printBtn = e.target.closest('[data-action="print"]');
    if (printBtn) {
      e.preventDefault();
      window.print();
    }
  });

  // Handle delete image action
  document.addEventListener('click', function (e) {
    const deleteBtn = e.target.closest('[data-action="delete-image"]');
    if (deleteBtn) {
      e.preventDefault();
      const imageId = deleteBtn.getAttribute('data-image-id');
      const imageName = deleteBtn.getAttribute('data-image-name');
      
      // Check if bootstrap modal exists (admin panel)
      const deleteModal = document.getElementById('deleteModal');
      if (deleteModal) {
        document.getElementById('deleteImageName').textContent = imageName;
        document.getElementById('deleteForm').action = 
          "{{ url_for('admin_images.delete', id=0) }}".replace('0', imageId);
        new bootstrap.Modal(deleteModal).show();
      }
    }
  });
});

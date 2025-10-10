const express = require('express');
const router = express.Router();
const calendarController = require('../../controllers/calendarController');

// ...existing code...

// Добавляем маршрут для получения доступных слотов по дате
router.get('/available_slots/:date', calendarController.getAvailableSlots);

// ...existing code...
module.exports = router;

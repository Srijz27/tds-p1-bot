const express = require('express');
const app = express();

app.use(express.json());

app.post('/prorate', (req, res) => {
  const { old_price, new_price, days_remaining, days_in_actual_month, spec } = req.body;

  if (
    typeof old_price !== 'number' ||
    typeof new_price !== 'number' ||
    typeof days_remaining !== 'number' ||
    (spec === 'v2' && typeof days_in_actual_month !== 'number') ||
    (spec !== 'v1' && spec !== 'v2')
  ) {
    return res.status(400).json({ error: 'Invalid request body' });
  }

  const priceDelta = new_price - old_price;
  let divisor;

  if (spec === 'v1') {
    divisor = 30;
  } else {
    divisor = days_in_actual_month;
  }

  const charge = priceDelta * (days_remaining / divisor);

  return res.json({ charge });
});

app.get('/', (req, res) => res.send('Proration endpoint is running.'));

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Listening on ${PORT}`));

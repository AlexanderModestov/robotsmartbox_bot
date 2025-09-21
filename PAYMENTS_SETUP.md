# Payment Integration Setup

This document explains how to set up Stripe payment integration for the RoboSmartBox bot.

## Features

- ✅ `/subscribe` command with localized premium subscription offers
- ✅ Stripe payment integration with webhook support
- ✅ Automatic user status update after successful payment
- ✅ Admin notifications for new subscriptions
- ✅ Payment verification and error handling

## Quick Start

### 1. Environment Variables

Add these to your `.env` file:

```env
# Stripe Configuration
STRIPE_PAYMENT_LINK=https://buy.stripe.com/your-payment-link
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
STRIPE_SECRET_KEY=sk_test_your_secret_key

# Optional: Webhook server port (default: 8000)
WEBHOOK_PORT=8000
```

### 2. Run with Payment Support

```bash
# Run bot with payment webhook server
python run_with_payments.py

# Or run just the bot (without payments)
python -m bot.main
```

## How It Works

### Subscription Flow

1. User sends `/subscribe` command
2. Bot shows premium features and pricing ($29/month)
3. User clicks "Subscribe Now" button → opens Stripe payment page
4. After successful payment → Stripe sends webhook to `/webhook/stripe`
5. Bot verifies payment and updates user status
6. User receives confirmation message

### Payment Processing

```
User Payment → Stripe → Webhook → Bot → Database Update → User Notification
```

### Webhook Endpoints

- `POST /webhook/stripe` - Stripe payment webhooks
- `GET /health` - Health check
- `GET /` - Service info

## Stripe Setup

### 1. Create Payment Link

1. Go to Stripe Dashboard → Payment Links
2. Create new payment link for $29/month subscription
3. Add metadata: `telegram_id={CHECKOUT_SESSION_CLIENT_REFERENCE_ID}`
4. Copy the payment link to `STRIPE_PAYMENT_LINK`

### 2. Configure Webhook

1. Go to Stripe Dashboard → Webhooks
2. Add endpoint: `https://your-domain.com/webhook/stripe`
3. Select events:
   - `checkout.session.completed`
   - `payment_intent.succeeded`
   - `invoice.payment_succeeded`
4. Copy webhook secret to `STRIPE_WEBHOOK_SECRET`

## Current Implementation

### User Status Tracking

Currently using existing database fields:
- `notification = true` indicates premium status
- Future: Will add dedicated subscription fields

### Supported Events

- `checkout.session.completed` - One-time payments
- `payment_intent.succeeded` - Payment confirmations
- `invoice.payment_succeeded` - Recurring subscriptions

### Security

- Webhook signature verification
- Request validation and error handling
- Secure customer data extraction

## Testing

### Local Testing

1. Use ngrok to expose local webhook endpoint:
   ```bash
   ngrok http 8000
   ```

2. Update Stripe webhook URL to ngrok URL

3. Test with Stripe test payments

### Webhook Testing

```bash
# Test webhook endpoint
curl -X POST http://localhost:8000/webhook/stripe \
  -H "Content-Type: application/json" \
  -d '{"type": "test"}'
```

## Troubleshooting

### Common Issues

1. **Webhook signature verification fails**
   - Check `STRIPE_WEBHOOK_SECRET` is correct
   - Ensure webhook endpoint is publicly accessible

2. **User not found after payment**
   - Verify `telegram_id` is included in Stripe metadata
   - Check user exists in database

3. **Payment not reflected in bot**
   - Check webhook server logs
   - Verify webhook events are being received

### Logs

Payment events are logged with format:
```
Payment event: checkout.session.completed, Telegram ID: 123456, Customer: cus_..., Amount: 29.0
```

## Next Steps

1. Add subscription expiration handling
2. Implement subscription cancellation
3. Add database fields for subscription tracking
4. Create admin dashboard for subscription management
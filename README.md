# 🛒 Smart Grocery Price Comparison & Train Delivery Availability Platform

## 📌 Overview

This project is a **decision-support grocery intelligence platform** designed to help users make **better purchasing decisions** for groceries and train journeys.

The platform enables users to:
1. Compare grocery prices across multiple online platforms and choose the best option based on **price, availability, and basket coverage**.
2. Check whether selected food or grocery items can be **delivered to a train journey** using official train food delivery systems operated by IRCTC and its authorized partners.

The application **does not process payments or deliveries**.  
Its role is to **analyze data, guide user decisions, and redirect users** to trusted platforms where the final transaction is completed.

---

## 🎯 Problem Statement

### Grocery Shopping Challenges
- Prices vary significantly across grocery platforms
- Items frequently go out of stock
- Users must manually check multiple apps
- Optimizing a full grocery basket is difficult
- Healthier or better alternatives are not easily discoverable

### Train Journey Food Challenges
- Passengers are unsure if food can be delivered to their train
- Confusion exists around authorized vendors
- Lack of clarity before placing an order

---

## ✅ Solution

This platform acts as an **intelligence layer** that:
- Compares grocery prices and availability across platforms
- Optimizes purchasing decisions at a **basket level**
- Suggests alternatives when items are unavailable
- Verifies **train delivery availability** using official systems
- Redirects users to original platforms for checkout

---

## 🧠 Core Design Philosophy

> **Guide the decision, not the transaction.**

- No payment handling  
- No logistics or delivery management  
- No on-demand scraping  
- Transparent data freshness and confidence  

---

## 🔁 High-Level System Flow


All heavy processing is performed in the background to ensure fast user interactions.

---

## 1️⃣ Feature: Grocery Price Comparison Engine

### 🔍 Feature Description

The Grocery Price Comparison Engine allows users to input a grocery list in any format and receive a **platform-wise comparison** that highlights the most cost-effective and reliable option for their complete basket.

The comparison focuses on **overall basket quality**, rather than individual item pricing.

---

### 🧩 Key Capabilities

- Multi-platform grocery comparison
- Basket-level price estimation
- Item availability and coverage scoring
- Smart substitution for unavailable items
- Explainable suggestions and recommendations

---

### 📊 Basket Ranking Logic

Platforms are ranked using the following criteria:
1. Basket coverage (available items / total items)
2. Estimated total basket price
3. Data freshness and confidence score
4. Optional user preferences

Example:
- Zepto – ₹420 – 10/10 items available  
- Blinkit – ₹399 – 8/10 items available  

In this case, Zepto may be recommended due to higher basket reliability.

---

### 🔄 Out-of-Stock Handling

When an item is unavailable:
- The user is clearly informed
- Similar alternatives are suggested
- Price increase is capped (e.g., within 15%)
- No replacement occurs without user approval

Examples:
- White bread → Brown bread  
- Milk 500ml → Milk 1L (better value option)

---

### 🔗 Redirect-Based Ordering

The application does **not place or manage orders**.  
Once the user selects a platform, they are redirected to the corresponding grocery app or website to complete checkout.

This approach avoids payment handling and delivery complexity.

---

## 2️⃣ Feature: Train Delivery Availability Integration

### 🚆 Feature Description

This feature checks whether selected food or grocery items can be delivered to a **train journey** using official train food delivery systems operated by IRCTC and its authorized partners.

---

### 🔁 Train Delivery Flow


---

### 🏢 Authorized Vendor Enforcement

- Only IRCTC-authorized vendors are considered
- Unauthorized or random restaurants are never shown
- Ensures compliance, hygiene, and food safety standards

---

### 💳 Payments and Fulfilment

- Payments are handled by IRCTC or partner platforms
- Vendors receive orders through official systems
- The application does not manage settlements, refunds, or delivery

---

## 🏗️ Technical Architecture (High-Level)


All crawling, scraping, and data updates occur asynchronously in the background.

---

## 🔒 Compliance and Safety

- No on-demand scraping
- No unauthorized API usage
- No payment or logistics handling
- Transparent pricing and freshness indicators
- Clear user disclaimers

---

## 🧪 Technologies Used

- Python
- PostgreSQL with pgvector
- Web crawling and scraping
- Sentence-transformer embeddings
- Retrieval-Augmented Generation (RAG)
- Background task processing
- Optional frontend using React or Next.js

---

## 🏁 Final Summary

This project is **not a grocery delivery application**.

It is a:
- Grocery price intelligence system
- Basket-level comparison and recommendation engine
- Train delivery availability guide

The platform helps users make **smarter, faster, and more confident decisions**, while keeping payments, logistics, and fulfilment on trusted external platforms.

> **The goal is to reduce cost, save time, and improve decision quality — without owning execution.**
import { Schema, model, models, type Document, Types } from "mongoose";

export type TransactionType = "BUY" | "SELL";

export interface ITransaction extends Document {
  _id: Types.ObjectId;
  userId: string;
  symbol: string;
  company: string;
  exchange: string;
  type: TransactionType;
  quantity: number;
  price: number;
  totalAmount: number;
  balanceAfter: number;
  timestamp: Date;
}

const TransactionSchema = new Schema<ITransaction>(
  {
    userId: {
      type: String,
      required: true,
      index: true,
    },
    symbol: {
      type: String,
      required: true,
      uppercase: true,
      trim: true,
    },
    company: {
      type: String,
      required: true,
      trim: true,
    },
    exchange: {
      type: String,
      required: true,
      trim: true,
      default: "US",
    },
    type: {
      type: String,
      enum: ["BUY", "SELL"],
      required: true,
    },
    quantity: {
      type: Number,
      required: true,
      min: 1,
    },
    price: {
      type: Number,
      required: true,
      min: 0,
    },
    totalAmount: {
      type: Number,
      required: true,
      min: 0,
    },
    balanceAfter: {
      type: Number,
      required: true,
      min: 0,
    },
    timestamp: {
      type: Date,
      default: Date.now,
      index: true,
    },
  },
  {
    timestamps: false, // We use our own timestamp field
  }
);

// Index for fetching user's transaction history sorted by time
TransactionSchema.index({ userId: 1, timestamp: -1 });

const Transaction = models?.Transaction || model<ITransaction>("Transaction", TransactionSchema);

export default Transaction;

import { Schema, model, models, type Document, Types } from "mongoose";

export interface IPortfolio extends Document {
  _id: Types.ObjectId;
  userId: string;
  symbol: string;
  company: string;
  exchange: string;
  quantity: number;
  averageBuyPrice: number;
  totalInvested: number;
  createdAt: Date;
  updatedAt: Date;
}

const PortfolioSchema = new Schema<IPortfolio>(
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
    quantity: {
      type: Number,
      required: true,
      min: 0,
    },
    averageBuyPrice: {
      type: Number,
      required: true,
      min: 0,
    },
    totalInvested: {
      type: Number,
      required: true,
      min: 0,
    },
  },
  {
    timestamps: true,
  }
);

// Prevent a user from having duplicate entries for the same stock
PortfolioSchema.index({ userId: 1, symbol: 1 }, { unique: true });

const Portfolio = models?.Portfolio || model<IPortfolio>("Portfolio", PortfolioSchema);

export default Portfolio;

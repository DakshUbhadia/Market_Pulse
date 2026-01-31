import { Schema, model, models, type Document } from "mongoose";

export interface IUser extends Document {
  email: string;
  name?: string;
  // Separate balances for Indian and US markets
  indianBalance: number;
  usBalance: number;
  // Legacy field (kept for backward compatibility, will be removed)
  virtualBalance?: number;
  virtualPortfolioValue?: number;
  createdAt: Date;
  updatedAt: Date;
}

const UserSchema = new Schema<IUser>(
  {
    email: {
      type: String,
      required: true,
      unique: true,
      lowercase: true,
      trim: true,
    },
    name: {
      type: String,
      trim: true,
    },
    // Indian market balance: ₹10,00,000 (10 lakh)
    indianBalance: {
      type: Number,
      default: 1000000,
      min: 0,
    },
    // US market balance: $100,000
    usBalance: {
      type: Number,
      default: 100000,
      min: 0,
    },
    // Legacy fields (kept for migration)
    virtualBalance: {
      type: Number,
      default: 100000,
      min: 0,
    },
    virtualPortfolioValue: {
      type: Number,
      default: 0,
      min: 0,
    },
  },
  {
    timestamps: true,
  }
);

const User = models?.User || model<IUser>("User", UserSchema);

export default User;

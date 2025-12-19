import { Schema, model, models, type Document } from "mongoose";

export type AlertType = "PRICE" | "PERCENTAGE" | "PE_RATIO";
export type AlertCondition = "GREATER_THAN" | "LESS_THAN" | "CROSSES_ABOVE" | "CROSSES_BELOW";
export type AlertFrequency = "ONCE" | "HOURLY" | "DAILY" | "MINUTELY" | "CUSTOM";

export interface WatchlistAlertDoc extends Document {
	userId: string;
	name: string;
	symbol: string;
	stockName: string;
	exchange: string;
	type: AlertType;
	condition: AlertCondition;
	threshold: number;
	frequency: AlertFrequency;
	isActive: boolean;
	createdAt: Date;
	updatedAt: Date;
	lastTriggeredAt?: Date;
	deleteAt?: Date;
	lastObservedValue?: number;
	lastObservedAt?: Date;
}

const AlertSchema = new Schema<WatchlistAlertDoc>(
	{
		userId: {
			type: String,
			required: true,
			index: true,
		},
		name: {
			type: String,
			required: true,
			trim: true,
		},
		symbol: {
			type: String,
			required: true,
			uppercase: true,
			trim: true,
			index: true,
		},
		stockName: {
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
			required: true,
			enum: ["PRICE", "PERCENTAGE", "PE_RATIO"],
		},
		condition: {
			type: String,
			required: true,
			enum: ["GREATER_THAN", "LESS_THAN", "CROSSES_ABOVE", "CROSSES_BELOW"],
		},
		threshold: {
			type: Number,
			required: true,
		},
		frequency: {
			type: String,
			required: true,
			enum: ["ONCE", "HOURLY", "DAILY", "MINUTELY", "CUSTOM"],
			default: "DAILY",
		},
		isActive: {
			type: Boolean,
			required: true,
			default: true,
		},
		lastTriggeredAt: {
			type: Date,
		},
		deleteAt: {
			type: Date,
			index: true,
		},
		lastObservedValue: {
			type: Number,
		},
		lastObservedAt: {
			type: Date,
		},
	},
	{ timestamps: true }
);

AlertSchema.index({ userId: 1, symbol: 1, name: 1 });

const Alert = models?.Alert || model<WatchlistAlertDoc>("Alert", AlertSchema);

export default Alert;

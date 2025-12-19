import { Schema, model, models, type Document } from "mongoose";

export interface EmailPreferencesDoc extends Document {
	userId: string;
	receiveDailyNewsSummary: boolean;
	receiveAlerts: boolean;
	createdAt: Date;
	updatedAt: Date;
}

const EmailPreferencesSchema = new Schema<EmailPreferencesDoc>(
	{
		userId: {
			type: String,
			required: true,
			index: true,
		},
		receiveDailyNewsSummary: {
			type: Boolean,
			required: true,
			default: true,
		},
		receiveAlerts: {
			type: Boolean,
			required: true,
			default: true,
		},
	},
	{ timestamps: true }
);

EmailPreferencesSchema.index({ userId: 1 }, { unique: true });

const EmailPreferences =
	models?.EmailPreferences || model<EmailPreferencesDoc>("EmailPreferences", EmailPreferencesSchema);

export default EmailPreferences;

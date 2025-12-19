'use server';

import { connectToDatabase } from "@/database/mongoose";
import EmailPreferences from "@/database/models/email-preferences.model";
import { requireCurrentUser } from "@/lib/actions/session.actions";

export type EmailPreferencesDTO = {
	receiveDailyNewsSummary: boolean;
	receiveAlerts: boolean;
};

const DEFAULT_PREFS: EmailPreferencesDTO = {
	receiveDailyNewsSummary: true,
	receiveAlerts: true,
};

export async function getMyEmailPreferences(): Promise<EmailPreferencesDTO> {
	try {
		const { userId } = await requireCurrentUser();
		await connectToDatabase();

		const doc = await EmailPreferences.findOne({ userId })
			.select({ receiveDailyNewsSummary: 1, receiveAlerts: 1 })
			.lean<{ receiveDailyNewsSummary?: boolean; receiveAlerts?: boolean }>();

		if (!doc) {
			await EmailPreferences.create({ userId, ...DEFAULT_PREFS });
			return { ...DEFAULT_PREFS };
		}

		return {
			receiveDailyNewsSummary:
				typeof doc.receiveDailyNewsSummary === "boolean" ? doc.receiveDailyNewsSummary : true,
			receiveAlerts: typeof doc.receiveAlerts === "boolean" ? doc.receiveAlerts : true,
		};
	} catch (err) {
		console.error("getMyEmailPreferences error:", err);
		return { ...DEFAULT_PREFS };
	}
}

export async function updateMyEmailPreferences(
	patch: Partial<EmailPreferencesDTO>
): Promise<{ success: boolean; preferences?: EmailPreferencesDTO; error?: string }> {
	try {
		const { userId } = await requireCurrentUser();
		await connectToDatabase();

		const update: Partial<EmailPreferencesDTO> = {};
		if (typeof patch.receiveDailyNewsSummary === "boolean") {
			update.receiveDailyNewsSummary = patch.receiveDailyNewsSummary;
		}
		if (typeof patch.receiveAlerts === "boolean") {
			update.receiveAlerts = patch.receiveAlerts;
		}

		// Avoid MongoDB conflict: the same field cannot appear in both $set and $setOnInsert.
		const setOnInsert: Record<string, unknown> = { userId };
		if (typeof update.receiveDailyNewsSummary !== "boolean") {
			setOnInsert.receiveDailyNewsSummary = DEFAULT_PREFS.receiveDailyNewsSummary;
		}
		if (typeof update.receiveAlerts !== "boolean") {
			setOnInsert.receiveAlerts = DEFAULT_PREFS.receiveAlerts;
		}

		await EmailPreferences.updateOne(
			{ userId },
			{ $set: update, $setOnInsert: setOnInsert },
			{ upsert: true }
		);

		const fresh = await EmailPreferences.findOne({ userId })
			.select({ receiveDailyNewsSummary: 1, receiveAlerts: 1 })
			.lean<{ receiveDailyNewsSummary?: boolean; receiveAlerts?: boolean }>();

		return {
			success: true,
			preferences: {
				receiveDailyNewsSummary:
					typeof fresh?.receiveDailyNewsSummary === "boolean" ? fresh.receiveDailyNewsSummary : true,
				receiveAlerts: typeof fresh?.receiveAlerts === "boolean" ? fresh.receiveAlerts : true,
			},
		};
	} catch (err) {
		console.error("updateMyEmailPreferences error:", err);
		return { success: false, error: err instanceof Error ? err.message : "Failed to update" };
	}
}

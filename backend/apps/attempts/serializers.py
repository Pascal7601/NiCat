from rest_framework import serializers

class SaveResponseSerializer(serializers.Serializer):
    selected_option_id = serializers.UUIDField(allow_null=True, required=False)
    text_answer = serializers.CharField(allow_blank=True, required=False, max_length=20000)
    def validate(self, data):
        if not any(k in data for k in ("selected_option_id", "text_answer")):
            raise serializers.ValidationError("Supply selected_option_id or text_answer")
        return data

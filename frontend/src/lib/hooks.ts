"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationOptions,
} from "@tanstack/react-query";

import {
  ApiError,
  ChannelHistoryResponse,
  ChannelState,
  CosignPayload,
  OpenChannelPayload,
  SettlementResponse,
  UpdateChannelPayload,
  apiClient,
} from "./api";

const queryKeys = {
  channelState: ["channel", "state"] as const,
  channelHistory: ["channel", "history"] as const,
};

export function useChannelState() {
  return useQuery<ChannelState, ApiError>({
    queryKey: queryKeys.channelState,
    queryFn: () => apiClient.getChannelState(),
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 404) {
        return false;
      }
      return failureCount < 1;
    },
  });
}

export function useChannelHistory(enabled: boolean) {
  return useQuery<ChannelHistoryResponse, ApiError>({
    queryKey: queryKeys.channelHistory,
    queryFn: () => apiClient.getChannelHistory(),
    enabled,
  });
}

type MutationConfig<TData, TVariables> = UseMutationOptions<
  TData,
  ApiError,
  TVariables
>;

export function useOpenChannel(config?: MutationConfig<ChannelState, OpenChannelPayload>) {
  const queryClient = useQueryClient();
  return useMutation<ChannelState, ApiError, OpenChannelPayload>({
    mutationFn: apiClient.openChannel,
    ...config,
    onSuccess: (data, variables, context) => {
      queryClient.setQueryData(queryKeys.channelState, data);
      queryClient.invalidateQueries({ queryKey: queryKeys.channelHistory });
      config?.onSuccess?.(data, variables, context);
    },
  });
}

export function useUpdateChannel(config?: MutationConfig<ChannelState, UpdateChannelPayload>) {
  const queryClient = useQueryClient();
  return useMutation<ChannelState, ApiError, UpdateChannelPayload>({
    mutationFn: apiClient.updateChannel,
    ...config,
    onSuccess: (data, variables, context) => {
      queryClient.setQueryData(queryKeys.channelState, data);
      queryClient.invalidateQueries({ queryKey: queryKeys.channelHistory });
      config?.onSuccess?.(data, variables, context);
    },
  });
}

export function useCosignChannel(config?: MutationConfig<ChannelState, CosignPayload>) {
  const queryClient = useQueryClient();
  return useMutation<ChannelState, ApiError, CosignPayload>({
    mutationFn: apiClient.cosignChannel,
    ...config,
    onSuccess: (data, variables, context) => {
      queryClient.setQueryData(queryKeys.channelState, data);
      config?.onSuccess?.(data, variables, context);
    },
  });
}

export function useCloseChannel(
  config?: MutationConfig<SettlementResponse, void>,
) {
  const queryClient = useQueryClient();
  return useMutation<SettlementResponse, ApiError, void>({
    mutationFn: () => apiClient.closeChannel({}),
    ...config,
    onSuccess: (data, variables, context) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.channelState });
      queryClient.invalidateQueries({ queryKey: queryKeys.channelHistory });
      config?.onSuccess?.(data, variables, context);
    },
  });
}

export { queryKeys };


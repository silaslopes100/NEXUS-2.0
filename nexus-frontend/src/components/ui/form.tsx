'use client'

import * as React from 'react'
import { useForm, type UseFormReturn, type SubmitHandler } from 'react-hook-form'
import { Controller, type ControllerProps } from 'react-hook-form'
import { cn } from '@/lib/utils'

interface FormProps extends React.FormHTMLAttributes<HTMLFormElement> {
  onSubmit: SubmitHandler<any>
}

const Form = ({ onSubmit, ...props }: FormProps) => (
  <form onSubmit={onSubmit} {...props} />
)

interface FormFieldProps {
  control: UseFormReturn<any>['control']
  name: string
  render: (field: {
    field: { onChange: (...args: any[]) => void; onBlur: () => void; name: string; value: any }
    fieldState: { invalid: boolean; isDirty: boolean; isTouched: boolean; error: any }
  }) => React.ReactElement
}

const FormField = ({ control, name, render, ...props }: FormFieldProps) => {
  return (
    <Controller control={control} name={name} render={render} {...props} />
  )
}

const FormItem = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('space-y-2', props.className)} {...props} />
  )
)
FormItem.displayName = 'FormItem'

const FormLabel = React.forwardRef<HTMLLabelElement, React.LabelHTMLAttributes<HTMLLabelElement>>(
  ({ className, ...props }, ref) => (
    <label ref={ref} className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70" {...props} />
  )
)
FormLabel.displayName = 'FormLabel'

const FormControl = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('', props.className)} {...props} />
  )
)
FormControl.displayName = 'FormControl'

const FormDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p ref={ref} className={cn('text-sm text-muted-foreground', props.className)} {...props} />
  )
)
FormDescription.displayName = 'FormDescription'

const FormMessage = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, children, ...props }, ref) => (
    <p ref={ref} className={cn('text-sm text-destructive', props.className)} {...props}>
      {children}
    </p>
  )
)
FormMessage.displayName = 'FormMessage'

export { Form, FormField, FormItem, FormLabel, FormControl, FormDescription, FormMessage }